param(
  # Back-compat: -BaseUrl maps to -BackendUrl.
  [Parameter(Mandatory=$false)]
  [Alias('BaseUrl')]
  [string]$BackendUrl = "http://127.0.0.1:7080",

  # Optional separate frontend host (e.g., https://www.codelaunchai.com).
  [Parameter(Mandatory=$false)]
  [string]$FrontendUrl = ""

  ,
  # Optional deeper checks that exercise the builder API flow:
  # create project -> plan -> state -> generate -> files -> materialize.
  [Parameter(Mandatory=$false)]
  [switch]$BuilderFlow,

  # If set with -BuilderFlow, also triggers a full Vite build on the backend.
  # This can be slow and resource intensive; use sparingly in prod.
  [Parameter(Mandatory=$false)]
  [switch]$BuildPreview,

  # If set, keeps the created smoke-test project instead of deleting it.
  [Parameter(Mandatory=$false)]
  [switch]$KeepProject
)

$ErrorActionPreference = 'Stop'

function Write-Result([string]$Label, [bool]$Ok, [string]$Detail = "") {
  if ($Ok) {
    Write-Host ("PASS: {0} {1}" -f $Label, $Detail)
  } else {
    Write-Host ("FAIL: {0} {1}" -f $Label, $Detail)
  }
  return $Ok
}

function Try-Request([scriptblock]$Fn) {
  try {
    return @{ ok=$true; value=(& $Fn) }
  } catch {
    $ex = $_.Exception
    $result = @{ ok=$false; error=$ex.Message }

    if ($ex.Response) {
      try {
        $resp = $ex.Response
        $result.status = [int]$resp.StatusCode
        $hdrs = @{}
        $resp.Headers.AllKeys | ForEach-Object { $hdrs[$_] = $resp.Headers[$_] }
        $result.headers = $hdrs

        try {
          $sr = New-Object System.IO.StreamReader($resp.GetResponseStream())
          $result.body = $sr.ReadToEnd()
          $sr.Close()
        } catch {
          # ignore body read errors
        }
      } catch {
        # ignore response parse errors
      }
    }

    return $result
  }
}

function Assert-Status([string]$Label, [int]$Actual, [int[]]$Allowed) {
  $ok = $Allowed -contains $Actual
  Write-Result $Label $ok ("(status={0})" -f $Actual)
  return $ok
}

$base = $BackendUrl.TrimEnd('/')
$frontend = $FrontendUrl.TrimEnd('/')
$allOk = $true
$warn = 0

$blueprint = $null
$planMeta = $null

# 1) /health
$r = Try-Request { Invoke-WebRequest -UseBasicParsing ("$base/health") }
if (-not $r.ok) {
  Write-Result "/health" $false $r.error
  exit 1
}
$allOk = (Assert-Status "/health" $r.value.StatusCode @(200)) -and $allOk

if ($frontend) {
  # 2) Frontend /app/ returns HTML
  $r2 = Try-Request { Invoke-WebRequest -UseBasicParsing ("$frontend/app/") }
  if ($r2.ok) {
    $ct = $r2.value.Headers['Content-Type']
    $allOk = (Assert-Status "FRONTEND /app/" $r2.value.StatusCode @(200)) -and $allOk
    $allOk = (Write-Result "Content-Type" ($ct -like "text/html*") ("(Content-Type={0})" -f $ct)) -and $allOk
  } else {
    Write-Result "FRONTEND /app/" $false $r2.error
    $allOk = $false
  }
} else {
  # 2) Backend / redirect -> /app/
  $r2 = Try-Request { Invoke-WebRequest -UseBasicParsing -MaximumRedirection 0 ("$base/") }
  if ($r2.ok) {
    $loc = $r2.value.Headers['Location']
    $allOk = (Assert-Status "/" $r2.value.StatusCode @(301,302,303,307,308)) -and $allOk
    $allOk = (Write-Result "Location header" ([string]::IsNullOrWhiteSpace($loc) -eq $false) ("(Location={0})" -f $loc)) -and $allOk
  } else {
    Write-Result "/" $false $r2.error
    $allOk = $false
  }

  # 3) Backend /app/ returns HTML
  $r3 = Try-Request { Invoke-WebRequest -UseBasicParsing ("$base/app/") }
  if ($r3.ok) {
    $ct = $r3.value.Headers['Content-Type']
    $allOk = (Assert-Status "/app/" $r3.value.StatusCode @(200)) -and $allOk
    $allOk = (Write-Result "Content-Type" ($ct -like "text/html*") ("(Content-Type={0})" -f $ct)) -and $allOk
  } else {
    Write-Result "/app/" $false $r3.error
    $allOk = $false
  }
}

# 4) /chat
$chatBody = @{ messages = @(@{ role='user'; content='hi' }); context = $null } | ConvertTo-Json -Depth 6
$r4 = Try-Request {
  Invoke-WebRequest -UseBasicParsing -Method Post ("$base/chat") -ContentType 'application/json' -Body $chatBody
}
if ($r4.ok) {
  $allOk = (Assert-Status "POST /chat" $r4.value.StatusCode @(200)) -and $allOk
} else {
  Write-Result "POST /chat" $false $r4.error
  $allOk = $false
}

# 5) /plan
$planBody = @{ goal = 'Build a simple landing page with pricing and contact.'; context = $null } | ConvertTo-Json -Depth 6
$r5 = Try-Request {
  Invoke-WebRequest -UseBasicParsing -Method Post ("$base/plan") -ContentType 'application/json' -Body $planBody
}
if ($r5.ok) {
  $allOk = (Assert-Status "POST /plan" $r5.value.StatusCode @(200)) -and $allOk
  try {
    $pj = $r5.value.Content | ConvertFrom-Json
    $blueprint = $pj.blueprint
    $planMeta = $pj.meta
  } catch {
    # Non-fatal; builder flow may be skipped.
    $blueprint = $null
  }
} else {
  if ($r5.error -match "\(402\)") {
    Write-Host "WARN: POST /plan credits-gated (402)"
    $warn++
  } else {
    Write-Result "POST /plan" $false $r5.error
    $allOk = $false
  }
}

if ($BuilderFlow.IsPresent) {
  Write-Host "INFO: Running builder flow checks..."

  if ($null -eq $blueprint) {
    Write-Host "WARN: Skipping builder flow: no blueprint available (plan failed or parsing failed)."
    $warn++
  } else {
    $projectId = $null

    # Create a smoke-test project
    $name = "SmokeTest " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    $createBody = @{ name = $name; project_id = $null } | ConvertTo-Json -Depth 6
    $rP = Try-Request {
      Invoke-WebRequest -UseBasicParsing -Method Post ("$base/projects") -ContentType 'application/json' -Body $createBody
    }
    if ($rP.ok) {
      $allOk = (Assert-Status "POST /projects" $rP.value.StatusCode @(200)) -and $allOk
      try {
        $p = $rP.value.Content | ConvertFrom-Json
        $projectId = $p.id
      } catch {
        $projectId = $null
      }
    } else {
      Write-Result "POST /projects" $false $rP.error
      $allOk = $false
    }

    if ($projectId) {
      # GET project
      $rPg = Try-Request { Invoke-WebRequest -UseBasicParsing ("$base/projects/$projectId") }
      if ($rPg.ok) {
        $allOk = (Assert-Status "GET /projects/{id}" $rPg.value.StatusCode @(200)) -and $allOk
      } else {
        Write-Result "GET /projects/{id}" $false $rPg.error
        $allOk = $false
      }

      # Persist state (blueprint + plan meta)
      $stateBody = @{ blueprint = $blueprint; plan = @{ goal = "smoke"; meta = $planMeta } } | ConvertTo-Json -Depth 100
      $rState = Try-Request {
        Invoke-WebRequest -UseBasicParsing -Method Put ("$base/projects/$projectId/state") -ContentType 'application/json' -Body $stateBody
      }
      if ($rState.ok) {
        $allOk = (Assert-Status "PUT /projects/{id}/state" $rState.value.StatusCode @(200)) -and $allOk
      } else {
        Write-Result "PUT /projects/{id}/state" $false $rState.error
        $allOk = $false
      }

      # Generate files
      $genBody = @{ blueprint = $blueprint; project_name = 'generated-app' } | ConvertTo-Json -Depth 100
      $rGen = Try-Request {
        Invoke-WebRequest -UseBasicParsing -Method Post ("$base/generate") -ContentType 'application/json' -Body $genBody
      }

      $files = @()
      if ($rGen.ok) {
        $allOk = (Assert-Status "POST /generate" $rGen.value.StatusCode @(200)) -and $allOk
        try {
          $gj = $rGen.value.Content | ConvertFrom-Json
          $files = @($gj.files)
        } catch {
          $files = @()
        }
      } else {
        if ($rGen.error -match "\(402\)") {
          Write-Host "WARN: POST /generate credits-gated (402)"
          $warn++
        } else {
          Write-Result "POST /generate" $false $rGen.error
          $allOk = $false
        }
      }

      # Persist a small subset of files (best-effort) to validate the endpoint
      if ($files.Count -gt 0) {
        $subset = @($files | Select-Object -First 25)
        $filesBody = @{ files = $subset } | ConvertTo-Json -Depth 100
        $rFiles = Try-Request {
          Invoke-WebRequest -UseBasicParsing -Method Put ("$base/projects/$projectId/files") -ContentType 'application/json' -Body $filesBody
        }
        if ($rFiles.ok) {
          $allOk = (Assert-Status "PUT /projects/{id}/files" $rFiles.value.StatusCode @(200)) -and $allOk
        } else {
          Write-Host ("WARN: PUT /projects/{id}/files failed: {0}" -f $rFiles.error)
          $warn++
        }
      }

      # Materialize workspace (writes the on-disk workspace)
      $matBody = @{ blueprint = $blueprint; project_name = 'generated-app' } | ConvertTo-Json -Depth 100
      $rMat = Try-Request {
        Invoke-WebRequest -UseBasicParsing -Method Post ("$base/projects/$projectId/materialize") -ContentType 'application/json' -Body $matBody
      }
      if ($rMat.ok) {
        $allOk = (Assert-Status "POST /projects/{id}/materialize" $rMat.value.StatusCode @(200)) -and $allOk
      } else {
        Write-Result "POST /projects/{id}/materialize" $false $rMat.error
        $allOk = $false
      }

      if ($BuildPreview.IsPresent) {
        Write-Host "INFO: Building preview (this can take a while)..."
        $rBuild = Try-Request {
          Invoke-WebRequest -UseBasicParsing -Method Post ("$base/projects/$projectId/build") -ContentType 'application/json' -TimeoutSec 600 -Body "{}"
        }
        if ($rBuild.ok) {
          $allOk = (Assert-Status "POST /projects/{id}/build" $rBuild.value.StatusCode @(200)) -and $allOk
        } else {
          Write-Host ("WARN: POST /projects/{id}/build failed: {0}" -f $rBuild.error)
          $warn++
        }
      }

      # Cleanup
      if (-not $KeepProject.IsPresent) {
        $rDel = Try-Request { Invoke-WebRequest -UseBasicParsing -Method Delete ("$base/projects/$projectId") }
        if ($rDel.ok) {
          $allOk = (Assert-Status "DELETE /projects/{id}" $rDel.value.StatusCode @(200)) -and $allOk
        } else {
          Write-Host ("WARN: DELETE /projects/{id} failed: {0}" -f $rDel.error)
          $warn++
        }
      } else {
        Write-Host ("INFO: KeepProject set; leaving smoke project id={0}" -f $projectId)
      }
    }
  }
}

# 6) Basic CORS preflight should not 400 (dev signal)
$origin = if ($frontend) { $frontend } else { 'http://localhost:3000' }
Write-Host ("INFO: CORS preflight Origin={0}" -f $origin)
$r6 = Try-Request {
  Invoke-WebRequest -UseBasicParsing -Method Options ("$base/projects") -Headers @{
    Origin=$origin
    'Access-Control-Request-Method'='GET'
    'Access-Control-Request-Headers'='content-type,authorization'
  }
}
if ($r6.ok) {
  $allOk = (Assert-Status "OPTIONS /projects" $r6.value.StatusCode @(200,204)) -and $allOk
} else {
  Write-Result "OPTIONS /projects" $false $r6.error
  if ($null -ne $r6.status) {
    Write-Host ("INFO: OPTIONS status={0}" -f $r6.status)
  }
  if ($r6.headers) {
    Write-Host "INFO: Response headers:"
    $r6.headers.GetEnumerator() | Sort-Object Name | ForEach-Object { Write-Host ("  {0}: {1}" -f $_.Key, $_.Value) }
  }
  if ($r6.body) {
    Write-Host "INFO: Response body:"
    Write-Host $r6.body
  }
  $allOk = $false
}

if ($allOk) {
  if ($warn -gt 0) {
    Write-Host ("\nSmoke test: OK (warnings={0})" -f $warn)
  } else {
    Write-Host "\nSmoke test: OK"
  }
  exit 0
}

Write-Host "\nSmoke test: FAILED"
exit 2

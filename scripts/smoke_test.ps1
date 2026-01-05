param(
  # Back-compat: -BaseUrl maps to -BackendUrl.
  [Parameter(Mandatory=$false)]
  [Alias('BaseUrl')]
  [string]$BackendUrl = "http://127.0.0.1:7080",

  # Optional separate frontend host (e.g., https://www.codelaunchai.com).
  [Parameter(Mandatory=$false)]
  [string]$FrontendUrl = ""
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
    return @{ ok=$false; error=$_.Exception.Message }
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
} else {
  if ($r5.error -match "\(402\)") {
    Write-Host "WARN: POST /plan credits-gated (402)"
    $warn++
  } else {
    Write-Result "POST /plan" $false $r5.error
    $allOk = $false
  }
}

# 6) Basic CORS preflight should not 400 (dev signal)
$r6 = Try-Request {
  Invoke-WebRequest -UseBasicParsing -Method Options ("$base/projects") -Headers @{
    Origin=($frontend ? $frontend : 'http://localhost:3000')
    'Access-Control-Request-Method'='GET'
    'Access-Control-Request-Headers'='content-type,authorization'
  }
}
if ($r6.ok) {
  $allOk = (Assert-Status "OPTIONS /projects" $r6.value.StatusCode @(200,204)) -and $allOk
} else {
  Write-Result "OPTIONS /projects" $false $r6.error
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

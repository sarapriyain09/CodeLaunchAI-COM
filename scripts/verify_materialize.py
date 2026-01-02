import pathlib
import sys

import requests


def main() -> int:
    base = "http://127.0.0.1:7080"

    r = requests.get(base + "/health", timeout=10)
    print("health", r.status_code)
    r.raise_for_status()

    r = requests.post(base + "/projects", json={"name": "Workspace Dir Test"}, timeout=10)
    print("create project", r.status_code)
    r.raise_for_status()
    project_id = r.json()["id"]
    print("project_id", project_id)

    blueprint = {
        "schema_version": "1.0",
        "app_type": "website",
        "goal": "Verify workspace materialization path",
        "target_audience": "internal testing",
        "branding": {
            "product_name": "WorkspaceDirTest",
            "tagline": "Testing materialize output",
            "logo_url": None,
        },
        "theme": {"style": "modern", "primary_color": None, "font_family": None},
        "routes": [
            {"path": "/", "title": "Home", "layout": "default"},
            {"path": "/contact", "title": "Contact", "layout": "default"},
        ],
        "components": [
            {"name": "HeroSection", "description": "Simple hero section", "used_on_routes": ["/"]},
            {
                "name": "ContactSection",
                "description": "Contact form area",
                "used_on_routes": ["/contact"],
            },
        ],
        "data_models": [],
        "integrations": [],
        "constraints": ["Use Tailwind", "Mobile-first"],
        "acceptance_criteria": ["Home page renders", "Contact page renders"],
    }

    payload = {"project_name": "workspacedir-test", "blueprint": blueprint}
    r = requests.post(base + f"/projects/{project_id}/materialize", json=payload, timeout=180)
    print("materialize", r.status_code)
    if r.status_code != 200:
        print(r.text[:800])
    r.raise_for_status()

    mat = r.json()
    workspace_path = pathlib.Path(mat["workspace_path"]).resolve()
    print("workspace_path", workspace_path)
    print("file_count", mat.get("file_count"))
    print("workspace exists", workspace_path.exists())

    checks = ["package.json", "index.html", "src/main.tsx", "src/App.tsx", ".gitignore"]
    for rel in checks:
        p = (workspace_path / rel).resolve()
        print(rel, "OK" if p.exists() else "MISSING")

    repo_generated = pathlib.Path(
        r"d:/Five_Pillar/07Software/SplendidTechnology/codelaunchcom/generated"
    ).resolve()
    print("repo generated dir", repo_generated)
    print(
        "workspace under generated?",
        str(workspace_path).lower().startswith(str(repo_generated).lower()),
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

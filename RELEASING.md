# Releasing

## Tagging convention

Releases use **semantic versioning** with a leading `v`: `vMAJOR.MINOR.PATCH`.

| Part | Bump when | Example |
|---|---|---|
| MAJOR | breaking change | `v1.0.0` → `v2.0.0` |
| MINOR | new backwards-compatible feature | `v1.0.0` → `v1.1.0` |
| PATCH | bug fix only | `v1.1.0` → `v1.1.1` |

Rules:

- Tags are **annotated** (`git tag -a`) with a message describing the release.
- The Docker image uses the **exact Git tag** as its tag: `hw3-flask-app:v1.1.0`. `latest` is never used.
- A version is **immutable**. If a release is wrong, ship a new version (`v1.1.1`) or roll back; never re-tag or overwrite. ECR is set to *Immutable* tags and the pipeline also refuses to push an existing tag.

## How to cut a release

```bash
git checkout main && git pull
# make and commit the change (via a feature branch + pull request), then:
git tag -a v1.1.0 -m "v1.1.0: add release banner"
git push origin v1.1.0
```

Pushing the tag fires the GitHub webhook. Jenkins accepts only `refs/tags/vX.Y.Z`, so ordinary branch commits do **not** start a build. The pipeline then runs *Build → Push to ECR → Deploy → Verify* with `ACTION=release`.

Publish the GitHub Release notes: repo → **Releases** → **Draft a new release** → choose the tag → *Generate release notes* → **Publish**.

## Manual actions (Build with Parameters)

| ACTION | What it does | Needs VERSION |
|---|---|---|
| `release` | build + push + deploy (what a tag push runs) | yes |
| `build` | build the image on the Jenkins machine only | yes |
| `push` | push an already-built local image to ECR | yes |
| `deploy` | deploy a version that already exists in ECR | yes |
| `rollback` | redeploy an older version from ECR, **no rebuild** | yes |

## How to roll back

1. Jenkins → job `hw3-release` → **Build with Parameters**
2. `ACTION = rollback`, `VERSION = v1.1.0` (the last good tag) → **Build**
3. The pipeline confirms that `v1.1.0` already exists in ECR, then runs
   `docker service update --image <ecr>/hw3-flask-app:v1.1.0 hw3_web` on the manager.
   Swarm replaces the replicas one at a time (`update_config`: `parallelism: 1`, `order: start-first`), so the service stays reachable.
4. Verify: open `http://18.143.120.217:8080`, or `curl http://18.143.120.217:8080/health` and check `"version"`.

To prove there is no downtime, run `scripts/uptime-check.sh http://18.143.120.217:8080` on your laptop during the rollback: every line stays `HTTP 200`.

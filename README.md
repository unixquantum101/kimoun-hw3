# Homework 3 — Release Management: GitHub Tags & Jenkins Build / Push / Deploy / Rollback

**Name:** SENG Kimoun
**GitHub repository:** https://github.com/unixquantum101/kimoun-hw3.git
**ECR repository:** `780603797333.dkr.ecr.ap-southeast-1.amazonaws.com/hw3-flask-app` (private, immutable tags, region `ap-southeast-1`)
**Live deployment:** http://18.143.120.217:8080 and http://52.221.163.83:8080 — currently running **v1.3.0**

## 1. What this project is

Homework 2 deployed on every commit. This version ships **versioned releases**: a Git tag
`vX.Y.Z` triggers Jenkins, which builds an image tagged with that exact version, pushes it to
a private Amazon ECR repository, and rolls it out to a Docker Swarm on EC2. A parameterized
Jenkins job can also **roll back** to any earlier version already stored in ECR, with no rebuild.

```
git tag v1.1.0 ─push─▶ GitHub ──webhook (tag only)──▶ Jenkins (local Ubuntu, ngrok)
                                                         │ build  hw3-flask-app:v1.1.0
                                                         │ push   ──▶ Amazon ECR (immutable tags)
                                                         │ deploy ──▶ Swarm manager ─ rolling update ─▶ manager + worker
ACTION=rollback VERSION=v1.0.0 ─▶ confirm image in ECR ─▶ docker service update --image (no rebuild)
```

## 2. Repository layout

```
.
├── app/                    # Flask app + Dockerfile (APP_VERSION baked in)
├── scripts/
│   ├── wait-converged.sh   # runs on the manager: waits for the rolling update to finish
│   └── uptime-check.sh     # run on a laptop: proves the service stays up during a rollback
├── docker-stack.yml        # Swarm stack: replicas, restart_policy, update_config (start-first)
├── Jenkinsfile             # parameterized pipeline: release | build | push | deploy | rollback
├── RELEASING.md            # tagging convention + how to release and roll back
└── README.md
```

## 3. Tagging convention

Semantic versioning, `vMAJOR.MINOR.PATCH`, annotated tags, one immutable image per tag.
Details are in [RELEASING.md](RELEASING.md).

| Tag | Meaning |
|---|---|
| `v1.0.0` | _first release_ |
| `v1.1.0` | _new feature_ |
| `v1.2.0` | _second release (the one rolled back)_ |
| `v1.3.0` | _third release (the one rolled back)_ |


## 4. How the pipeline works

| Stage | Runs for | What it does |
|---|---|---|
| Resolve action & version | all | Reads `ACTION`/`VERSION` (or the pushed tag), validates `vX.Y.Z` |
| Checkout tag | release, build, deploy | Checks out exactly `refs/tags/<VERSION>` |
| Guard: tag must be new | release, push | Fails if that tag already exists in ECR (immutability) |
| Build image | release, build | `docker build` with `APP_VERSION`, `GIT_SHA`, `BUILD_NUMBER` build args |
| Push to ECR | release, push | `aws ecr get-login-password` → `docker push …:<VERSION>` |
| Confirm image exists in ECR | deploy, rollback | `aws ecr describe-images` — rollback aborts if the version is missing |
| Deploy | release, deploy | `docker stack deploy --with-registry-auth` on the manager |
| Rollback | rollback | `docker service update --image …:<VERSION>` — **no rebuild**, rolling update |
| Verify & record | release, deploy, rollback | Waits for convergence, prints `/health`, appends to the deployment log |

**Tag-only trigger:** the Generic Webhook Trigger filter accepts only `refs/tags/vX.Y.Z`
(and `deleted=false`). A push to a branch returns 200 from Jenkins but starts no build.

**No-downtime rollback:** `update_config` sets `parallelism: 1` and `order: start-first`, so
Swarm starts the replacement task before stopping the old one, one replica at a time.

## 5. Jenkins & AWS setup (summary)

- Jenkins on local Ubuntu 24.04, public via ngrok `https://stank-level-cocoa.ngrok-free.dev`; plugins: Git, Pipeline, Credentials Binding, **Generic Webhook Trigger**.
- Credentials: `aws-ecr-creds` (IAM user limited to ECR), `swarm-manager-ssh` (SSH key for the manager).
- GitHub webhook: `https://stank-level-cocoa.ngrok-free.dev/generic-webhook-trigger/invoke?token=hw3-release`, `application/json`, *Just the push event*.
- ECR repo `hw3-flask-app` with **tag immutability = Immutable**.
- Swarm: 1 manager + 1 worker (`docker node ls` → both Ready). Security group: 22 from my IP, 8080 public, 2377/7946/4789 inside the group only.

## 6. How to verify

1. **Release:** `git tag -a v1.x.0 -m "..." && git push origin v1.x.0` → a build starts by itself and all stages go green.
2. **ECR:** several tags (`v1.0.0`, `v1.1.0`, …) are listed and none was overwritten.
3. **Running version:** `curl http://18.143.120.217:8080/health` shows the version in `"version"`.
4. **Rollback:** run the job with `ACTION=rollback`, `VERSION=<older tag>`; `/health` now shows the older version and `scripts/uptime-check.sh` showed only `HTTP 200`.

## 7. Deployment history

Appended automatically by the pipeline to `/home/ubuntu/deploy-history.log` on the manager.

| Time (UTC) | Action | Version | Jenkins build |
|---|---|---|---|
| _paste from `cat ~/deploy-history.log`_ | release | v1.0.0 | #_ |
| | release | v1.1.0 | #_ |
| | release | v1.2.0 | #_ |
| | **rollback** | v1.1.0 | #_ |

Version running at submission time: **_vX.Y.Z_**

## 8. Screenshots

| File | Shows |
|---|---|
| `screenshots/01-github-tags.png` | GitHub Tags / Releases page with 3+ versions |
| `screenshots/02-ecr-images.png` | ECR repo with all version tags |
| `screenshots/03-release-build.png` | Jenkins build started by a tag push, all stages green |
| `screenshots/04-webhook-delivery.png` | GitHub webhook delivery for the tag (200) |
| `screenshots/05-rollback-build.png` | Rollback build with parameters and green stages |
| `screenshots/06-uptime-during-rollback.png` | `uptime-check.sh` output, only HTTP 200, version changing |
| `screenshots/07-running-app.png` | App in the browser showing the running version |

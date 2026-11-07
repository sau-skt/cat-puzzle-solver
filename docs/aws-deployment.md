# AWS deployment plan

This document is a deployment design. It does not create cloud resources and it does not spend money.

## Recommended layout

| Piece | Service | Role |
| --- | --- | --- |
| Web and API containers | ECS Fargate, or one EC2 instance running Docker Compose for a small install | Run the frontend nginx image and the backend image |
| Database | RDS MySQL 8 | Replace the Compose MySQL service. Keep the same schema via Alembic. |
| Uploaded screenshots | S3 | Store original and normalized images. The API currently writes to a local volume; point `STORAGE_DIR` at a mounted volume first, then move object storage behind `app/services/storage.py`. |
| Traffic | Application Load Balancer | Terminate HTTPS with ACM. Forward `/` to the frontend target group and, if the frontend nginx is not used as the only origin, `/api` to the backend. |
| Secrets | Secrets Manager | `JWT_SECRET`, database password, SMTP password, S3 credentials. Inject them as task environment variables. Do not bake them into images. |
| Logs | CloudWatch | Ship uvicorn and nginx logs. |

## Settings that must change

- `DATABASE_URL` uses the RDS hostname.
- `JWT_SECRET` is a long random value from Secrets Manager.
- `COOKIE_SECURE=true` and the site is served only over HTTPS.
- `DEBUG_RETURN_TOKENS=false`.
- `REQUIRE_EMAIL_VERIFICATION=true` once SMTP is set.
- `CORS_ORIGINS` is the public site origin only.
- `APP_PUBLIC_URL` is the https origin used in reset emails.

## Network

Put ECS tasks and RDS in private subnets. The load balancer is the only public entry. Security groups allow the backend to reach RDS on 3306 and nothing else to reach the database.

## Images

Build `backend/Dockerfile` and `frontend/Dockerfile` in CI and push them to ECR. Run `alembic upgrade head` as the backend entrypoint before uvicorn starts, which the image already does.

## What is intentionally not done

No AWS account calls, no Terraform apply, and no public bucket. Implement the S3 storage adapter when you are ready to leave local disk.

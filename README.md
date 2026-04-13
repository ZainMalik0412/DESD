# BRFN App — ECS Fargate Deployment

Django marketplace application deployed on AWS ECS Fargate with full CI/CD, zero-downtime deployments, and infrastructure-as-code.

**Live URL:** https://brfnapp.com

---

## Architecture Overview

```
Internet
    │
    ▼
┌─────────────────────────────────────────────────┐
│  Route 53 (brfnapp.com)                         │
│       │                                         │
│       ▼                                         │
│  ACM Certificate (TLS 1.3)                      │
│       │                                         │
│       ▼                                         │
│  WAF v2 ──► ALB (public subnets)                │
│                  │                              │
│       ┌──────────┴──────────┐                   │
│       ▼                     ▼                   │
│  ECS Task 1            ECS Task 2               │
│  (private subnet)      (private subnet)         │
│       │                     │                   │
│       ├──► RDS MySQL (private subnet)           │
│       ├──► ElastiCache Redis (private subnet)   │
│       └──► SQS Queue                            │
│                                                 │
│  VPC Endpoints (no NAT gateway)                 │
│  ├── ECR (ecr.api + ecr.dkr)                   │
│  ├── S3 (gateway — free)                        │
│  ├── CloudWatch Logs                            │
│  ├── Secrets Manager                            │
│  └── SQS                                       │
└─────────────────────────────────────────────────┘
```

### Key Components

| Component | Service | Purpose |
|-----------|---------|---------|
| **Compute** | ECS Fargate | Runs Django in Docker containers |
| **Load Balancer** | ALB + WAF | HTTPS termination, routing, DDoS/SQLi protection |
| **Database** | RDS MySQL 8.0 | Primary data store (encrypted, daily backups) |
| **Cache** | ElastiCache Redis 7 | Session/query caching layer |
| **Queue** | SQS | Event messaging (future integration ready) |
| **DNS** | Route 53 | brfnapp.com → ALB |
| **TLS** | ACM | Auto-renewing wildcard certificate |
| **Secrets** | Secrets Manager | DB credentials, Django key, Stripe keys |
| **Container Registry** | ECR | Docker image storage with vulnerability scanning |
| **Logs** | CloudWatch | Centralized ECS container logs (30-day retention) |

---

## Database Justification

**Choice: RDS MySQL 8.0**

- The existing application's `docker-compose.yml`, CI/CD pipeline (`collab.yml`), and `start.sh` are all built around MySQL.
- Django `settings.py` already configures MySQL as the primary production engine.
- `mysqlclient` is in `requirements.txt` and the Dockerfile installs `mariadb-connector-c`.
- Switching to PostgreSQL would require updating CI services, the docker-compose, the entrypoint script, and testing for ORM compatibility — added risk for zero benefit in this context.
- RDS MySQL provides encryption at rest, automated daily backups (7-day retention), and auto-scaling storage (20–50 GB).

**Trade-off:** PostgreSQL has richer feature support (JSONB, CTEs, etc.), but MySQL is the path of least resistance given the existing codebase. If schema complexity grows, migration to Aurora PostgreSQL is straightforward.

---

## No NAT Gateway — VPC Endpoints

Instead of NAT gateways (~$32/month/AZ), we use VPC endpoints:

| Endpoint | Type | Cost | Purpose |
|----------|------|------|---------|
| S3 | Gateway | **Free** | ECR image layer storage |
| ECR API | Interface | ~$7/mo | Docker registry API |
| ECR DKR | Interface | ~$7/mo | Docker image pull |
| CloudWatch Logs | Interface | ~$7/mo | Container log shipping |
| Secrets Manager | Interface | ~$7/mo | Secret injection at task start |
| SQS | Interface | ~$7/mo | Queue access |

**Total: ~$35/month** vs ~$64/month for 2 NAT gateways. VPC endpoints also keep traffic within the AWS network (lower latency, higher security).

---

## Deployment Workflow

### Code Merge to Live Traffic

```
Developer pushes to feature branch
         │
         ▼
┌─────────────────────────────┐
│  collab.yml                 │
│  1. Install dependencies    │
│  2. Run Django checks       │
│  3. Run migrations          │
│  4. Run all unit tests      │
│  5. Build Docker image      │
│  6. Auto-merge to main      │
└────────────┬────────────────┘
             │ (push to main)
             ▼
┌─────────────────────────────┐
│  deploy.yml                 │
│  1. OIDC auth (no keys)    │
│  2. Build Docker image      │
│  3. Push to ECR (sha tag)   │
│  4. Register new task def   │
│  5. Update ECS service      │
│  6. Wait for stability      │
│  7. Verify health           │
└─────────────────────────────┘
```

### Zero-Downtime Mechanism

1. **Rolling update**: `deployment_minimum_healthy_percent = 100%` ensures old tasks stay running until new ones are healthy.
2. **Health check grace period**: 180 seconds for Django to start (migrations, static collection, gunicorn boot).
3. **ALB health checks**: `/health/` endpoint checked every 30s. 2 healthy checks to register, 3 unhealthy to deregister.
4. **Circuit breaker**: If new tasks fail health checks, ECS automatically rolls back to the previous task definition revision.
5. **Container health check**: Python-level check runs inside the container every 30s with 120s start grace period.

### Rollback

- **Automatic**: ECS deployment circuit breaker detects failed health checks → reverts to last known-good task definition.
- **Manual**: `aws ecs update-service --cluster brfnapp-cluster --service brfnapp-web --task-definition brfnapp-web:<previous_revision> --force-new-deployment`

### Infrastructure Changes

Infrastructure changes (`infrastructure/**`) trigger `infra.yml`:
1. `terraform plan` on PRs (review before apply)
2. `terraform apply` on merge to main

---

## Manual Setup Steps

These steps are required **once** before the first deployment.

### Prerequisites

- AWS CLI v2 configured with admin credentials (`aws configure`)
- Terraform >= 1.7.0 installed
- Docker installed
- Domain `brfnapp.com` purchased on Route 53 (already done)

### Step 1: Create Terraform State Backend

```bash
# S3 bucket for state
aws s3api create-bucket \
  --bucket brfnapp-terraform-state \
  --region eu-west-2 \
  --create-bucket-configuration LocationConstraint=eu-west-2

aws s3api put-bucket-versioning \
  --bucket brfnapp-terraform-state \
  --versioning-configuration Status=Enabled

aws s3api put-public-access-block \
  --bucket brfnapp-terraform-state \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# DynamoDB table for state locking
aws dynamodb create-table \
  --table-name brfnapp-terraform-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region eu-west-2
```

### Step 2: Configure Terraform Variables

```bash
cd infrastructure
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars — set github_org and github_repo
```

### Step 3: Apply Terraform

```bash
cd infrastructure
terraform init
terraform plan    # Review the plan
terraform apply   # Creates all AWS resources (~5-10 minutes)
```

Note the outputs:
```
ecr_repository_url     = "123456789.dkr.ecr.eu-west-2.amazonaws.com/brfnapp/web"
github_actions_role_arn = "arn:aws:iam::123456789:role/brfnapp-github-actions"
```

### Step 4: Push Initial Docker Image

```bash
# Get ECR login
aws ecr get-login-password --region eu-west-2 | \
  docker login --username AWS --password-stdin <ECR_REPOSITORY_URL without /brfnapp/web>

# Build and push
docker build -t brfnapp-web .
docker tag brfnapp-web:latest <ECR_REPOSITORY_URL>:latest
docker push <ECR_REPOSITORY_URL>:latest

# Force ECS to pick up the image
aws ecs update-service \
  --cluster brfnapp-cluster \
  --service brfnapp-web \
  --force-new-deployment
```

### Step 5: Update Secrets

```bash
# Update Stripe keys (replace placeholders)
aws secretsmanager put-secret-value \
  --secret-id brfnapp/stripe-publishable-key \
  --secret-string "pk_test_your_actual_key"

aws secretsmanager put-secret-value \
  --secret-id brfnapp/stripe-secret-key \
  --secret-string "sk_test_your_actual_key"
```

### Step 6: Configure GitHub Repository

1. Go to GitHub repo → Settings → Secrets and variables → Actions
2. Add repository secret: `AWS_ROLE_ARN` = the `github_actions_role_arn` from Terraform output
3. All subsequent deployments use OIDC — no AWS access keys needed

### Step 7: Verify

```bash
# Check ECS service
aws ecs describe-services --cluster brfnapp-cluster --services brfnapp-web \
  --query 'services[0].{status:status,running:runningCount,desired:desiredCount}'

# Check ALB health
curl -s https://brfnapp.com/health/
# Expected: {"status": "ok"}
```

---

## Security

### IAM Least Privilege

| Role | Permissions |
|------|-------------|
| **ECS Execution** | Pull ECR images, read specific Secrets Manager secrets, push CloudWatch Logs |
| **ECS Task** | Send/receive SQS messages on `brfnapp-events` queue only |
| **GitHub Actions** | ECR push to `brfnapp/web`, ECS deploy, Terraform state S3/DynamoDB, scoped infra management |

### No Long-Lived Credentials

- GitHub Actions uses **OIDC federation** — temporary STS tokens, no `AWS_ACCESS_KEY_ID` stored
- Database password generated by Terraform's `random_password`, stored in Secrets Manager
- Django secret key auto-generated, stored in Secrets Manager
- Stripe keys stored in Secrets Manager (not in environment variables or code)

### WAF Protection

- AWS Managed Common Rule Set (XSS, traversal, etc.)
- AWS Managed Known Bad Inputs
- AWS Managed SQL Injection protection
- IP-based rate limiting (2000 req/5min per IP)

### Network Isolation

- ECS tasks, RDS, Redis all in **private subnets** with no internet route
- Only the ALB sits in public subnets
- Security groups enforce strict source restrictions (ALB→ECS→RDS/Redis)

---

## Local Development

```bash
docker compose up --build
# App: http://localhost:8000
# Redis: localhost:6379
# LocalStack SQS: localhost:4566
```

---

## Tear Down

**WARNING: ALB + WAF cost money even when idle.**

```bash
# Option 1: GitHub Actions (recommended)
# Go to Actions → "Destroy" → Run workflow → type "destroy"

# Option 2: Local
cd infrastructure
terraform destroy
```

Then clean up the state backend:
```bash
aws s3 rb s3://brfnapp-terraform-state --force
aws dynamodb delete-table --table-name brfnapp-terraform-lock
```

---

## Cost Estimate (idle)

| Resource | ~Monthly Cost |
|----------|--------------|
| ALB | $16 |
| WAF | $5 + $1/rule |
| ECS Fargate (2 × 0.25vCPU/512MB) | $15 |
| RDS db.t3.micro | $13 |
| ElastiCache cache.t3.micro | $12 |
| VPC Interface Endpoints (5) | $35 |
| ECR | < $1 |
| SQS | < $1 |
| **Total** | **~$100/month** |

Scale down `desired_count` to 1 and tear down when not needed.

---

## Project Structure

```
├── infrastructure/          # Terraform IaC
│   ├── main.tf              # Provider, backend
│   ├── variables.tf         # Input variables
│   ├── outputs.tf           # Output values
│   ├── vpc.tf               # VPC, subnets, VPC endpoints
│   ├── security_groups.tf   # SG rules
│   ├── alb.tf               # Load balancer, target group, listeners
│   ├── waf.tf               # WAF web ACL
│   ├── ecs.tf               # Cluster, task definition, service
│   ├── ecr.tf               # Container registry
│   ├── rds.tf               # MySQL database
│   ├── elasticache.tf       # Redis cache
│   ├── sqs.tf               # Message queue
│   ├── iam.tf               # IAM roles (ECS, GitHub OIDC)
│   ├── route53.tf           # DNS records
│   ├── acm.tf               # TLS certificate
│   └── secrets.tf           # Secrets Manager
├── .github/workflows/
│   ├── collab.yml           # CI: test + auto-merge
│   ├── deploy.yml           # CD: build → ECR → ECS
│   ├── infra.yml            # Terraform plan/apply
│   └── destroy.yml          # Terraform destroy
├── Dockerfile               # Multi-stage build
├── docker-compose.yml       # Local dev (MySQL + Redis + LocalStack)
└── start.sh                 # Entrypoint: migrations + static files
```

---

## Known Considerations

1. **Migrations on every task start**: `start.sh` runs `python manage.py migrate` on every container boot. With multiple ECS tasks, this is safe (Django migrations are idempotent) but adds startup time. For faster deployments, consider a separate one-off migration ECS task.

2. **Demo seeding**: `start.sh` runs `seed_database` on every start. In production, you may want to remove this or make it conditional (`if [ "$SEED_DB" = "true" ]`).

3. **Media files**: User-uploaded files go to local container storage (ephemeral on Fargate). For production persistence, add S3 storage with `django-storages`.

4. **Redis integration**: ElastiCache Redis is provisioned and the `REDIS_URL` env var is injected. To use it, add `django-redis` to `requirements.txt` and configure `CACHES` in `settings.py`.

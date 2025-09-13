
---

# IDEM WOKER FOR DOCKER IMAGE BUILDER (AWS ECR Public)

This project is a **Docker worker** that:

* Clones a Git repository
* Finds the `Dockerfile`
* Builds a Docker image
* Creates (if needed) a **public AWS ECR repository**
* Tags and pushes the image
* Writes the full image name into an `output.json` file

---

## ⚡ Requirements

* **Docker** installed
* **AWS account** with `AmazonElasticContainerRegistryPublicFullAccess` permissions
* AWS environment variables configured:

```bash
export AWS_ACCESS_KEY_ID=xxxx
export AWS_SECRET_ACCESS_KEY=yyyy
export AWS_DEFAULT_REGION=us-east-1
```

---

## 🔨 Build the worker image

```bash
docker build -t git-docker-worker-public .
```

---

## ▶️ Usage

```bash
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/results:/results \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION \
  git-docker-worker-public \
  --git-url https://github.com/USER/REPO.git \
  --repo-name my-public-repo \
  --tag v1 \
  --output /results/output.json
```

---

## 📦 Output

The `results/output.json` file will contain:

```json
{
  "image": "public.ecr.aws/<account-id>/my-public-repo:v1"
}
```

---

## 📝 Example

```bash
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/results:/results \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e AWS_DEFAULT_REGION=us-east-1 \
  git-docker-worker-public \
  --git-url https://github.com/docker-library/hello-world.git \
  --repo-name hello-world-public \
  --tag v1 \
   --output /results/output.json

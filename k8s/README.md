# Install for k8s
This was deployed on a k3s environment

## Deploy
1. Buld `grabber\Dockerfile` and push to Docker registry. (I use a Harbor instance)
2. Adjust **grabber.yml** and set image path
3. Adjust needed secret variables in **grabber-secret.yml** and deploy
4. Adjust storage classes in **pvc.yml** (I use Synology)
5. Apply using Kustomize **kustomization.yaml**
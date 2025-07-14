docker run -p 8080:8080 mi-flask-app:latest

id: plated-mantis-464301-k9
- gcloud config set project plated-mantis-464301-k9
1) Generar la imagen
- gcloud builds submit --tag gcr.io/plated-mantis-464301-k9/gen-ai-rag:latest
2) Desplegar en Cloud run
- gcloud run deploy apigenairag --image gcr.io/plated-mantis-464301-k9/gen-ai-rag:latest --platform managed --region us-west4 --allow-unauthenticated

https://apigenairag-559894288581.us-west4.run.app
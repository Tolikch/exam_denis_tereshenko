# Передача экзамена преподавателю

Передайте только файл `denis-tereshchenko-exam-bundle.tar` из папки `outputs`.

На компьютере преподавателя должен быть установлен и запущен Docker Desktop. После этого:

```bash
docker load -i denis-tereshchenko-exam-bundle.tar
docker volume create denis-exam-data
docker volume create denis-exam-submissions
docker run -d --name denis-exam -p 8000:8000 \
  -v denis-exam-data:/app/data \
  -v denis-exam-submissions:/app/submissions \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e EXECUTOR_VOLUME=denis-exam-submissions \
  -e ADMIN_LOGIN=admin \
  -e ADMIN_PASSWORD=admin \
  -e SECRET_KEY=change-this-secret \
  lfd-exam:latest
```

Открыть: `http://localhost:8000`.

Архив включает сайт и образы Python/Java. После `docker load` интернет не потребуется. Данные экзамена сохраняются в Docker volume `denis-exam-data`.

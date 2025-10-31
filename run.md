docker compose down -v  
docker compose build --no-cache app
docker compose up -d ollama
docker compose run --rm -e OLLAMA_HOST=http://ollama:11434 ollama pull gemma3:4b # (이미 받았으면 스킵 가능)
docker compose up app

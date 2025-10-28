FROM ollama/ollama:latest

RUN echo "FROM gemma3:4b" > /gemma3_Modelfile
RUN ollama create gemma3-custom -f /gemma3_Modelfile

RUN echo "FROM mxbai-embed-large" > /mxbai_Modelfile
RUN ollama create mxbai-embed-large-custom -f /mxbai_Modelfile

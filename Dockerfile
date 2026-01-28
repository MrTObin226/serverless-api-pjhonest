FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04
RUN pip install runpod diffusers transformers accelerate requests pillow
COPY handler.py /handler.py
CMD [ "python", "-u", "/handler.py" ]
FROM public.ecr.aws/lambda/python:3.13

# install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# copy requirements file
COPY pyproject.toml ${LAMBDA_TASK_ROOT}/

# sync dependencies
RUN uv venv
RUN uv pip sync pyproject.toml

# copy handler code
COPY handler.py ${LAMBDA_TASK_ROOT}/

# set PYTHONPATH to include the virtual environment site-packages
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}/.venv/lib/python3.13/site-packages"

# set the CMD to your handler
CMD [ "handler.exif_handler"]

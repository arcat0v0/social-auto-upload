# 使用 Ubuntu 22.04 基础镜像
FROM ubuntu:22.04

# 设置环境变量以避免可能的对话交互问题
ENV DEBIAN_FRONTEND=noninteractive

# 安装Python3和pip
RUN apt-get update && apt-get install -y python3-pip python3-dev

# 创建工作目录
WORKDIR /app

# 将当前目录内容复制到工作目录
COPY . /app

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium firefox

# 暴露应用程序运行的端口
EXPOSE 8000

# 启动命令，使用 uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

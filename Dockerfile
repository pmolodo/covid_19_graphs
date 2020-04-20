# From host, run:
# docker run -d -p 80:80 --restart always elrond79/covid19

FROM centos:8.1.1911


# Perhaps break this section out into it's own
# centos-anaconda image?
WORKDIR /usr/src/anaconda
ENV CONDA_INSTALLER Anaconda3-2020.02-Linux-x86_64.sh
ENV CONDA_DIR /usr/local/anaconda3
RUN dnf install curl
RUN curl https://repo.anaconda.com/archive/${CONDA_INSTALLER} -o ${CONDA_INSTALLER}
RUN bash ${CONDA_INSTALLER} -p ${CONDA_DIR} -b
RUN ${CONDA_DIR}/condabin/conda init
ENV CONDA ${CONDA_DIR}/condabin/conda

WORKDIR /usr/src/covid19
EXPOSE 80
COPY ./environment.yml .
RUN ${CONDA} env create -f environment.yml

COPY co-est2019-alldata.zip ./
COPY WPP2019_TotalPopulationBySex.zip ./
COPY covid19 run_server.bash ./
ENV BOKEH_ALLOW_WS_ORIGIN phonymammoth.com:80,mycustomgraph.com:80
CMD ["./run_server.bash"]


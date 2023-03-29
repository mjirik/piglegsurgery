#!/bin/bash

echo "DOCKERLOGNAME=${DOCKERLOGNAME}"
# there is primary log in .txt file and 3 rotating backup logs
sudo service redis-server start 2>&1 | \
#   tee >(rotatelogs -n 3 logs/piglegcv_${DOCKERLOGNAME}_redis_log.txt.bck 1M) | \
   rotatelogs -n 1 logs/piglegcv_${DOCKERLOGNAME}_redis_log.txt 1M
python worker.py 2>&1 | \
#   tee >(rotatelogs -n 3 logs/worker_${DOCKERLOGNAME}_log_0.txt.bck 1M) | \
   rotatelogs -n 1 logs/worker_${DOCKERLOGNAME}_log_0.txt 1M &
python worker.py 2>&1 | \
#   tee >(rotatelogs -n 3 logs/worker_${DOCKERLOGNAME}_log_1.txt.bck 1M) | \
   rotatelogs -n 1 logs/worker_${DOCKERLOGNAME}_log_1.txt 1M &
#python worker.py 2>&1 | \
#   tee >(rotatelogs -n 3 logs/worker_${DOCKERLOGNAME}_log_2.txt.bck 1M) | \
#   rotatelogs -n 1 logs/worker_${DOCKERLOGNAME}_log_2.txt 1M &

python app.py 2>&1 | \
   tee >(rotatelogs -n 3 logs/app_${DOCKERLOGNAME}_log.txt.bck 1M) | \
   rotatelogs -n 1 logs/app_${DOCKERLOGNAME}_log.txt 1M &
echo "Services started"


# Run jupyter lab

HOMEDIR=/storage/plzen1/home/$USER # substitute username and path to to your real username and path
HOSTNAME=`hostname -f`
JUPYTER_PORT="8808"
HOMEDIR=`eval echo ~$USER`

#find nearest free port to listen
isfree=$(netstat -taln | grep $JUPYTER_PORT)
while [[ -n "$isfree" ]]; do
    JUPYTER_PORT=$[JUPYTER_PORT+1]
    isfree=$(netstat -taln | grep $JUPYTER_PORT)
done

# move into $HOME directory
cd $HOMEDIR
if [ ! -f ./.jupyter/jupyter_notebook_config.json ]; then
   echo "jupyter passwd reset!"
   mkdir -p .jupyter/
   #here you can commem=nt randomly generated password and set your password
   pass=`dd if=/dev/urandom count=1 2> /dev/null | uuencode -m - | sed -ne 2p | cut -c-12` ; echo $pass
   #pass="SecretPassWord"
   hash=`singularity exec $SING_IMAGE python -c "from notebook.auth import passwd ; hash = passwd('$pass') ; print(hash)" 2>/dev/null`
   cat > .jupyter/jupyter_notebook_config.json << EOJson
{
  "NotebookApp": {
      "password": "$hash"
    }
}
EOJson
  PASS_MESSAGE="Your password was set to '$pass' (without ticks)."
else
  PASS_MESSAGE="Your password was already set before."
fi

cd /webapps/piglegsurgery/ && jupyter lab --no-browser --port $JUPYTER_PORT 2>&1 | \
#   tee >(rotatelogs -n 3 logs/jupyterlab_${DOCKERLOGNAME}_log_2.txt.bck 1M) | \
   rotatelogs -n 1 logs/jupyterlab_${DOCKERLOGNAME}_log.txt 1M &
echo "jupyterlab started"

printf "Job with JupiterLab was started.\n\
Use URL  http://$HOSTNAME:$JUPYTER_PORT\n\
$PASS_MESSAGE\n\
You can reset password by deleting file $HOMEDIR/.jupyter/jupyter_notebook_config.json and run job again with this script.\n"

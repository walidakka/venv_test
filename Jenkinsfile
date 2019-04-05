def packages_bucket = "lambda-deployment-packages-pipeline-test"
def logs_bucket = "lambda-deployment-packages-pipeline-test"
def key = ""
def wait = 10
node {
 try {
  // Clean workspace before doing anything
  cleanWs()
  deleteDir()
  // get branch source code
  stage('Clone') {
   checkout scm
  }
  // run unit testss
  /*stage('Unit-Test') {
   sh "ls"
   sh "python3 -m pytest tests/test_lambda_unit.py"
  }*/
  // package the lambda function and push to s3
  stage('Package') {
   sh "pip install -r requirements.txt -t ."
   sh "rm -rf tests requirements.txt"
   key = "venv/${determineRepoName()}/${commitID()}.zip"
   sh "zip -r ${commitID()}.zip -r *"
   sh "aws s3 cp ${commitID()}.zip s3://${packages_bucket}/${key}"
  }
  withEnv(['AWS_DEFAULT_REGION=eu-west-1']) {
    // deploy the test Lambda
    stage('Deploy Test Function') {
     sh "python lambda_ci.py deploy_test -f ${determineRepoName()} -b ${packages_bucket} -k ${key} -B ${env.BRANCH_NAME}"
    }
    // check for lambda Errors metric
    stage('Test') {
     sh "python lambda_ci.py test -f test-${determineRepoName()}-${env.BRANCH_NAME} -w ${wait}"
    }

 }

 } catch (err) {
  currentBuild.result = 'FAILED'
  throw (err)
 } finally {
  def mb_name = env.JOB_NAME.split('/')[0]
  sh """
  cat $JENKINS_HOME/jobs/${mb_name}/branches/${env.BRANCH_NAME}/builds/${env.BUILD_NUMBER}/log > build.log
  aws s3 cp build.log s3://${logs_bucket}/jenkins/${determineRepoName()}-${env.BRANCH_NAME}-${env.BUILD_NUMBER}.log
  """
  deleteDir()
 }
}

String determineRepoName() {
 return scm.getUserRemoteConfigs()[0].getUrl().tokenize('/').last().split("\\.")[0]
}

def commitID() {
 sh 'git rev-parse HEAD > .git/commitID'
 def commitID = readFile('.git/commitID').trim()
 sh 'rm .git/commitID'
 commitID
}

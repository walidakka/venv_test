def queueurl = 'https://sqs.eu-west-1.amazonaws.com/222015089569/lambda-testing'
def sleeptime = "2s"
def bucket = "lambda-deployment-packages-pipeline-test"
def key = ""
def wait = 120
node {
 // Clean workspace before doing anything
 cleanWs()
 deleteDir()
// get branch code
 stage('Clone') {
   sh "rm -rf *"
   checkout scm
 }
 // run unit test
 stage('Unit-Test') {
   sh "pytest lambda_code/tests/test_lambda_unit.py"
 }
 // package the lambda function and push to s3
 stage('Package') {
   key = "${determineRepoName()}/${commitID()}.zip"
   sh "zip ${commitID()}.zip lambda_code/*.py"
   sh "aws s3 cp ${commitID()}.zip s3://${bucket}/${key}"
 }
 // deploy the test Lambda and check for errors
 stage('Deploy-test') {
   sh "python3 check_lambdas.py -f ${determineRepoName()} -b ${bucket} -k ${key} -w ${wait}"
 }
 if(env.BRANCH_NAME == 'master'){
     stage("Upload"){
        sh "echo 'promote to prod'"
        }
      }
 stage('clean') {
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

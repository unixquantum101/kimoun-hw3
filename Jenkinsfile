// Homework 3 - tag-triggered releases + on-demand rollback
//
// ACTION   release  = build + push + deploy   (what a tag push runs automatically)
//          build    = build the image locally only
//          push     = push an already-built local image to ECR
//          deploy   = deploy a version that already exists in ECR
//          rollback = redeploy an older version already in ECR - NO rebuild
// VERSION  semantic-version tag, e.g. v1.2.0 (empty when started by a tag push)
//
// Trigger: GitHub push webhook -> Generic Webhook Trigger plugin. The filter below
// lets only refs/tags/vX.Y.Z through, so ordinary branch commits never start a build.

pipeline {
  agent any

  parameters {
    choice(name: 'ACTION',
           choices: ['release', 'build', 'push', 'deploy', 'rollback'],
           description: 'What to do. A tag push always runs "release".')
    string(name: 'VERSION', defaultValue: '',
           description: 'Target tag such as v1.2.0. Leave empty when triggered by a tag push.')
  }

  triggers {
    GenericTrigger(
      genericVariables: [
        [key: 'GIT_REF',     value: '$.ref'],
        [key: 'GIT_DELETED', value: '$.deleted']
      ],
      causeString: 'Tag push $GIT_REF',
      token: 'hw3-release',
      printContributedVariables: true,
      printPostContent: false,
      regexpFilterText: '$GIT_REF $GIT_DELETED',
      regexpFilterExpression: '^refs/tags/v[0-9]+\\.[0-9]+\\.[0-9]+ false$'
    )
  }

  options {
    timestamps()
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '30'))
  }

  environment {
    // ---- EDIT THESE FOUR VALUES ----------------------------------------
    AWS_REGION    = 'ap-southeast-1'
    AWS_ACCOUNT   = '123456789012'
    ECR_REPO      = 'hw3-flask-app'
    SWARM_MANAGER = 'ubuntu@MANAGER_PUBLIC_IP'
    // --------------------------------------------------------------------
    STACK_NAME    = 'hw3'
    REGISTRY      = "${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com"
  }

  stages {

    stage('Resolve action & version') {
      steps {
        script {
          env.ACT = params.ACTION ?: 'release'

          def v = (params.VERSION ?: '').trim()
          if (!v && env.GIT_REF) {
            v = env.GIT_REF.replaceFirst('^refs/tags/', '')
          }
          if (!(v ==~ /^v\d+\.\d+\.\d+$/)) {
            error "VERSION must look like v1.2.0 (got '${v}'). " +
                  "If this is the first run after editing the Jenkinsfile, it only registers " +
                  "the parameters and trigger - run it again with ACTION and VERSION set."
          }
          env.VERSION_TAG = v
          env.IMAGE_URI   = "${env.REGISTRY}/${env.ECR_REPO}:${v}"
          currentBuild.displayName = "#${env.BUILD_NUMBER} ${env.ACT} ${v}"
          echo "ACTION=${env.ACT}  VERSION=${v}  IMAGE=${env.IMAGE_URI}"
        }
      }
    }

    stage('Checkout tag') {
      when { expression { ['release', 'build', 'deploy'].contains(env.ACT) } }
      steps {
        checkout([$class: 'GitSCM',
                  branches: [[name: "refs/tags/${env.VERSION_TAG}"]],
                  userRemoteConfigs: scm.userRemoteConfigs,
                  extensions: [[$class: 'CloneOption', noTags: false, shallow: false]]])
        script {
          env.SHORT_SHA = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
        }
      }
    }

    stage('Guard: tag must be new') {
      when { expression { ['release', 'push'].contains(env.ACT) } }
      steps {
        script {
          withAccess {
            // Immutable tags: refuse to publish a version that already exists in ECR.
            def rc = sh(returnStatus: true, script: '''
              aws ecr describe-images --region $AWS_REGION --repository-name $ECR_REPO \
                --image-ids imageTag=$VERSION_TAG > /dev/null 2>&1
            ''')
            if (rc == 0) {
              error "Image ${env.VERSION_TAG} already exists in ECR. Tags are immutable - cut a new version instead."
            }
            echo "OK: ${env.VERSION_TAG} is not in ECR yet."
          }
        }
      }
    }

    stage('Build image') {
      when { expression { ['release', 'build'].contains(env.ACT) } }
      steps {
        sh '''
          docker build --build-arg APP_VERSION=$VERSION_TAG --build-arg GIT_SHA=$SHORT_SHA --build-arg BUILD_NUMBER=$BUILD_NUMBER -t $IMAGE_URI app/
        '''
      }
    }

    stage('Push to ECR') {
      when { expression { ['release', 'push'].contains(env.ACT) } }
      steps {
        script {
          withAccess {
            sh '''
              docker image inspect $IMAGE_URI > /dev/null 2>&1 || { echo "Image $IMAGE_URI is not built on this machine - run ACTION=build first."; exit 1; }
              aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $REGISTRY
              docker push $IMAGE_URI
            '''
          }
        }
      }
    }

    stage('Confirm image exists in ECR') {
      when { expression { ['deploy', 'rollback'].contains(env.ACT) } }
      steps {
        script {
          withAccess {
            // Rollback must reuse an image that is ALREADY in ECR - it never builds.
            sh '''
              aws ecr describe-images --region $AWS_REGION --repository-name $ECR_REPO --image-ids imageTag=$VERSION_TAG --query 'imageDetails[0].{tags:imageTags,pushed:imagePushedAt,digest:imageDigest}' --output table
            '''
          }
        }
      }
    }

    stage('Deploy (stack deploy)') {
      when { expression { ['release', 'deploy'].contains(env.ACT) } }
      steps {
        script {
          withAccess {
            sh '''
              SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=accept-new"
              scp $SSH_OPTS docker-stack.yml scripts/wait-converged.sh $SWARM_MANAGER:/home/ubuntu/
              aws ecr get-login-password --region $AWS_REGION | ssh $SSH_OPTS $SWARM_MANAGER "docker login --username AWS --password-stdin $REGISTRY"
              ssh $SSH_OPTS $SWARM_MANAGER "IMAGE=$IMAGE_URI docker stack deploy --with-registry-auth -c /home/ubuntu/docker-stack.yml $STACK_NAME"
            '''
          }
        }
      }
    }

    stage('Rollback (service update)') {
      when { expression { env.ACT == 'rollback' } }
      steps {
        // Rollback never checks out a tag or builds; it only needs the helper script from main.
        checkout scm
        script {
          withAccess {
            // `service update --image` uses the service's update_config:
            // one replica at a time, start-first -> the app stays reachable.
            sh '''
              SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=accept-new"
              scp $SSH_OPTS scripts/wait-converged.sh $SWARM_MANAGER:/home/ubuntu/
              echo "--- running BEFORE rollback:"
              ssh $SSH_OPTS $SWARM_MANAGER "docker service inspect --format '{{.Spec.TaskTemplate.ContainerSpec.Image}}' ${STACK_NAME}_web"
              aws ecr get-login-password --region $AWS_REGION | ssh $SSH_OPTS $SWARM_MANAGER "docker login --username AWS --password-stdin $REGISTRY"
              ssh $SSH_OPTS $SWARM_MANAGER "docker service update --with-registry-auth --detach=false --image $IMAGE_URI ${STACK_NAME}_web"
            '''
          }
        }
      }
    }

    stage('Verify & record') {
      when { expression { ['release', 'deploy', 'rollback'].contains(env.ACT) } }
      steps {
        script {
          withAccess {
            sh '''
              SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=accept-new"
              ssh $SSH_OPTS $SWARM_MANAGER "bash /home/ubuntu/wait-converged.sh ${STACK_NAME}_web 2"
              ssh $SSH_OPTS $SWARM_MANAGER "docker service ps ${STACK_NAME}_web --no-trunc --format 'table {{.Name}}\t{{.Image}}\t{{.CurrentState}}' | head -n 8"
              echo "--- /health on the manager:"
              ssh $SSH_OPTS $SWARM_MANAGER "curl -fsS http://localhost:8080/health"
              echo
              ssh $SSH_OPTS $SWARM_MANAGER "echo '$(date -u +%Y-%m-%dT%H:%M:%SZ) | $ACT | $VERSION_TAG | jenkins build #$BUILD_NUMBER' >> /home/ubuntu/deploy-history.log"
              echo "--- deployment history:"
              ssh $SSH_OPTS $SWARM_MANAGER "cat /home/ubuntu/deploy-history.log"
            '''
          }
        }
      }
    }
  }

  post {
    always {
      sh 'docker logout $REGISTRY || true'
    }
    success {
      echo "${env.ACT} ${env.VERSION_TAG} finished OK"
    }
    failure {
      echo 'Pipeline failed - check the red stage.'
    }
  }
}

// Binds the AWS keys and the SSH key for the enclosed steps.
def withAccess(Closure body) {
  withCredentials([
    usernamePassword(credentialsId: 'aws-ecr-creds',
                     usernameVariable: 'AWS_ACCESS_KEY_ID',
                     passwordVariable: 'AWS_SECRET_ACCESS_KEY'),
    sshUserPrivateKey(credentialsId: 'swarm-manager-ssh',
                      keyFileVariable: 'SSH_KEY')
  ]) {
    body()
  }
}

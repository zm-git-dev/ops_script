#!/bin/bash
set -x

### Used as part of a jenkins build.
### Need to have WORKSPACE  /  BUILD_ID  /  BUILD_NUMBER and  defined

export MAJOR=1
export MINOR=0
export PATCH=5
export FIXBUG=201119
## 更新内容，英文描述
export RELEASE_NOTE_EN="update note1"
## 更新内容，中文描述
export RELEASE_NOTE_CN="更新内容"

export PATH=/usr/bin:/home/jenkins_01:$PATH
#export VERSION_STRING=${MAJOR}.${MINOR}.${PATCH}.${BUILD_NUMBER}
export VERSION_STRING=${MAJOR}.${MINOR}.${PATCH}.${FIXBUG}
export SHORT_VERSION=${MAJOR}.${MINOR}.${PATCH}

export VERSION_NAME="paaz.v"${VERSION_STRING}
export PACKAGE_NAME=${VERSION_NAME}".zip"
export PACKAGE_FOLDER=${WORKSPACE}"/"${VERSION_NAME}

## 创建构建目录
mkdir ${PACKAGE_FOLDER}

init_data=/home/jenkins_01/ztron/db_data/init_data_1
update_sql=/home/jenkins_01/ztron/myGit/bp-database
cp -fr /home/jenkins_01/ztron/app_software /home/jenkins_01/ztron/software ${PACKAGE_FOLDER}

rm -fr ${PACKAGE_FOLDER}/app_software/appMarketClient/downloadImg
rm -fr ${PACKAGE_FOLDER}/app_software/file_manage/init_data
#rm -fr ${WORKSPACE}/app_software/postgresql/pginit1.0.tar.gz
cd /opt/sysoft
#tar -zcvf ${WORKSPACE}/app_software/postgresql/pginit1.0.tar.gz pgsql_init
cd -
ln -s ${init_data} ${PACKAGE_FOLDER}/app_software/file_manage/init_data

echo ${PACKAGE_NAME} > ${PACKAGE_FOLDER}/app_software/version.txt

cp -fr ${update_sql}/*sql ${PACKAGE_FOLDER}/app_software/migration

app_client=${PACKAGE_FOLDER}/app_software/appMarketClient/server/ztron-app-client.jar
# rm logs
rm -fr ${PACKAGE_FOLDER}/app_software/biopass_web/biopass_web.log*
rm -fr ${PACKAGE_FOLDER}/app_software/bp_auto_app/logs/*
rm -fr ${PACKAGE_FOLDER}/app_software/zlims-pro/backup/*
rm -fr ${PACKAGE_FOLDER}/app_software/wdl_script/.delete_sql/*

rm -fr .build 2>/dev/null
mkdir -p .build
cd .build
unzip ${app_client}
sed -i 's/active: .\+/active: prod/g' BOOT-INF/classes/application.yml
sed -i 's#appMgrBaseUrl:  .\+#appMgrBaseUrl:  https://ztron.mgitech.cn:443#' BOOT-INF/classes/application-prod.yml
jar -cvfM0 ztron-app-client.jar ./
mv ./ztron-app-client.jar ${app_client}
sed -i 's/config.test/config.prd/g' ${PACKAGE_FOLDER}/app_software/appMarketClient/web/systemctlStart.sh
sed -i "s/global.CONFIG_APP_MGR_SERVER_HOST = '.\+'/global.CONFIG_APP_MGR_SERVER_HOST = 'ztron.mgitech.cn'/" ${WORKSPACE}/app_software/appMarketClient/web/utils/config.js
sed -i "s/global.CONFIG_APP_MGR_SERVER_PORT = [0-9]\+/global.CONFIG_APP_MGR_SERVER_PORT = 443/" ${WORKSPACE}/app_software/appMarketClient/web/utils/config.js

cd ${PACKAGE_FOLDER}/..
cp ${PACKAGE_FOLDER}/app_software/wdl_script/paaz_install.sh ${PACKAGE_FOLDER}/installer.sh
cp ${PACKAGE_FOLDER}/app_software/wdl_script/paaz_update.sh ${PACKAGE_FOLDER}/update.sh
zip -r ${PACKAGE_NAME} ${VERSION_NAME}

## 构建升级包
export UPDATE_PACKAGE=${WORKSPACE}"/"update_package
export sql_folder=${UPDATE_PACKAGE}/sqls
mkdir -p ${sql_folder}
cp -fr ${update_sql}/* ${sql_folder}
mv ${sql_folder}/metadata.txt ${UPDATE_PACKAGE}
sed -i "s/__RELEASE_NOTE_EN__/${RELEASE_NOTE_EN}/" ${UPDATE_PACKAGE}/metadata.txt
sed -i "s/__RELEASE_NOTE_CN__/${RELEASE_NOTE_CN}/" ${UPDATE_PACKAGE}/metadata.txt
sed -i "s/__VERSION__/${VERSION_STRING}/" ${UPDATE_PACKAGE}/metadata.txt
## 准备每个组件的升级包
cp -fr ${PACKAGE_FOLDER}/app_software/appMarketClient/web ${UPDATE_PACKAGE}
cp -fr ${PACKAGE_FOLDER}/app_software/appMarketClient/server/ztron-app-client.jar ${UPDATE_PACKAGE}
cp -fr ${PACKAGE_FOLDER}/app_software/file_manage/api_dev/ztron-auto-store.war ${UPDATE_PACKAGE}
cp -fr ${PACKAGE_FOLDER}/app_software/file_manage/api_dev/ztron-storage-manage.war ${UPDATE_PACKAGE}
cp -fr ${PACKAGE_FOLDER}/app_software/file_manage/init_data/ztron-file2file.jar ${UPDATE_PACKAGE}
cp -fr ${PACKAGE_FOLDER}/app_software/system_manage/system-manage.jar ${UPDATE_PACKAGE}
cp -fr ${PACKAGE_FOLDER}/app_software/zlims-pro/nlims/MGI-ZLIMS-PRO.jar ${UPDATE_PACKAGE}
cp -fr ${PACKAGE_FOLDER}/app_software/zlims-pro/zsm/tomcat/webapps/MGI-ZSM.war ${UPDATE_PACKAGE}
cp -fr ${PACKAGE_FOLDER}/app_software/biopass_web ${UPDATE_PACKAGE}
cp -fr ${PACKAGE_FOLDER}/app_software/bp_auto_app ${UPDATE_PACKAGE}

cd ${UPDATE_PACKAGE}
zip -r paaz_update.zip ./
md5=`md5sum paaz_update.zip | awk '{print $1}'`
mv paaz_update.zip ${WORKSPACE}/paaz.v${VERSION_STRING}.${md5}.zip


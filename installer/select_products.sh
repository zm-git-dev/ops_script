cd /home/ztron/app_software/zlims-pro/init_product; 
cmd=`sh /home/ztron/app_software/wdl_script/nlims_execute_sql.sh /home/ztron/app_software/zlims-pro/init_product/get_products.sql | sed -e '1,2d' | sed -e '$d' | sed -e '$d' | xargs | perl -lane 'print("zenity --list --checklist --width 400 --height 250 --text=\"Select Products\" --column=\"Select\" --column=\"Product lists\" FALSE ".join(" FALSE ", @F))'`;
echo "select_option=\`$cmd\`;products=\$(echo \${select_option} | sed -e 's/|/,/g');sh init_product.sh \${products}" > /home/ztron/app_software/zlims-pro/init_product/.tmp.sh;
sh /home/ztron/app_software/zlims-pro/init_product/.tmp.sh;
#select_option=`$cmd`;
#products=$(echo ${select_option} | sed -e 's/|/ /g');
#echo "sh init_product.sh ${products}"

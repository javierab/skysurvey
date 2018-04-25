PRO make_commands
	
files=file_search('files/*.fits')

openw,lun,'idl_commands.txt',/get_lun
FOR i=0L,n_elements(files)-1 DO BEGIN
   tmp=strsplit(files[i],'.',/extract)
   tmp2=strsplit(tmp[0],'/',/extract)
   outname='plots/'+strtrim(tmp2[1],2)+'.ps'
   printf,lun,'get_footprint,"' + strtrim(files[i],2) + '","' + $
          strtrim(outname,2)+'"',format='(A)'
ENDFOR
free_lun,lun

END


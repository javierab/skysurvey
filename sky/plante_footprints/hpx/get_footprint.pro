PRO get_footprint,inmap,outfile,format=format

  IF ~keyword_set(format) THEN format='ring'
  
  read_fits_map,inmap,map

  test=size(map)
  IF (test[0] NE 1) THEN map=map[*,0]

  nside=fix(sqrt(n_elements(map)/12.))
  healpix_coords,nside,ra,dec,coord='G',format=format
  used=where(map GT 0)

  IF (round(min(ra[used])) EQ 0) THEN minx=0 ELSE $
     minx=round(min(ra[used]))-5.
  IF (round(max(ra[used])) EQ 360) THEN maxx=360 ELSE $
     maxx=round(max(ra[used]))+5.
  IF (round(min(dec[used])) EQ -90) THEN miny=-90 ELSE $
     miny=round(min(dec[used]))-5
  IF (round(max(dec[used])) EQ -90) THEN maxy=-90 ELSE $
     maxy=round(max(dec[used]))+5

  
  circsym,/fill
  cgPS_open,filename=outfile
  plot,ra[used],dec[used],psym=8,symsize=0.5,$
       xra=[minx,maxx],yra=[miny,maxy],xsty=1,ysty=1
  cgPS_close,/png

;  FOR i=0L,n_elements(used)-1 DO BEGIN
;     counter,i,n_elements(used)
;     neighbours_ring,nside,used[i],neighbors
;     xx=where(map[neighbors] EQ 0,cnt)
;     IF (cnt GT 1) THEN BEGIN
;        IF (n_elements(pix) EQ 0) THEN pix=used[i] ELSE $
;           pix=[pix,used[i]]
;     ENDIF
;  ENDFOR
;  plot,ra[pix],dec[pix],psym=8,xra=[0,360],yra=[-15,90],xsty=1,ysty=1
     
END

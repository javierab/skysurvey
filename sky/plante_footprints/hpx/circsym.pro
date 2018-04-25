;+
;  NAME:
;    circsym
;  PURPOSE:
;    Initialize a (filled) circle for plotting (psym=8)
;
;  USE:
;    circsym,/fill
;
;  INPUT:
;    
;  OPTIONAL INPUT:
;    
;  KEYWORDS:        
;    fill - set to provide filled circle
;    thick - set thickness of circle (must be set here,
;            as setting thick in the plot call will not work)
;
;  OUTPUT:
;    
;  NOTES:
;    
;  HISTORY:
;    2013 - Written - MAD (UWyo)
;    2015 - Cleaned and documented - MAD (UWyo)
;-
PRO circsym,fill=fill,thick=thick

IF ~keyword_set(thick) THEN thick=1
A = findgen(17)*(!PI*2/16.)

IF keyword_set(fill) THEN $
   usersym,cos(A),sin(A),/fill,thick=thick ELSE $
      usersym,cos(A),sin(A),thick=thick

return

END

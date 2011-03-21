from django.utils import simplejson
from django.http import HttpResponse

class JSONResponse(HttpResponse):
    """ JSON response class """
    def __init__(self,content='',json_opts={},mimetype="application/json",*args,**kwargs):
        
        if content:
            content = simplejson.dumps(content,**json_opts)
        else:
            content = simplejson.dumps([],**json_opts)

        super(JSONResponse,self).__init__(content,mimetype,*args,**kwargs)

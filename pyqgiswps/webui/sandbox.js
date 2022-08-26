
/*
 * Test sandbox
 */

sample_pr_data = {
  "expiration": 86400,
  "expire_at": "2018-03-22T16:59:05.754979Z",
  "identifier": "petra:computelandscapemetrics",
  "message": "Unable to execute algorithm\nIncorrect parameter value for INPUT_RASTER", 
  "percent_done": -1,
  "pinned": false,
  "status": "ERROR_STATUS",
  "status_url": "http://onfi-cluster-0.snap.lizlan:8200/petra/ows/?service=WPS&request=GetResults&uuid=29ea7892-2d29-11e8-b39e-0254d567f739",
  "execute_async": true, 
  "store_url": "http://onfi-cluster-0.snap.lizlan:8200/petra/store/29ea7892-2d29-11e8-b39e-0254d567f739/?service=WPS", 
  "time_end": "2018-03-21T16:59:05.754979Z",
  "time_start": "2018-03-21T16:59:05.495468Z",
  "timeout": 1800,
  "timestamp": 1521651545.754966,
  "uuid": "29ea7892-2d29-11e8-b39e-0254d567f739",
  "version": "1.0.0",
}

function insert_dummy_pr() {
    var uid   = Math.random().toString(36).substring(2)
               + (new Date()).getTime().toString(36);
    var index = Math.floor(Math.random() * 4 );
    var st = ['_WAIT','_RUN','ERROR_STATUS','DONE_STATUS'][index]
    sample_pr_data.status = st
    sample_pr_data.uuid   = uid
    if ( st == '_WAIT' ) {
      sample_pr_data.percent_done = -1
    } else if (st == '_RUN') {
      sample_pr_data.percent_done =  Math.floor(Math.random() * 100 )    
    } else if (st == 'DONE_STATUS') {
      sample_pr_data.percent_done = 100
    }
    add_process( sample_pr_data )
}





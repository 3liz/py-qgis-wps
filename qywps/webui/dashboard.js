
PROCESSES = new Map()

function get_pr_status( pr_data ) {
    // Return the status of
    if (pr_data.status == 'ERROR_STATUS') {
        return 'error';
    }
    if (pr_data.status == 'DONE_STATUS') {
        return 'done'
    }
    if (pr_data.percent_done == -1) {
        return 'wait'
    }
    if (pr_data.percent_done > 0) {
        return 'run'        
    }
    return 'none';
}

function format_iso_date( isodate ) {
    // Format an iso date to local date
    return (new Date(isodate)).toLocaleString();
}

function set_label( el, name, value ) {
    // Set the value of a label from the parent
    let lbl = el.querySelector('[name='+name+']')
    lbl.dataset.value = value
}

function update_progressbar( el, value ) {
    let progress = el.querySelector('[name=pr-progress] .progress-bar')
    progress.setAttribute('aria-valuenow', value )
    progress.style.width = value+'%'
}

function add_process( pr_data ) {
    // Get our template
    let t  = document.getElementById("pr-template")
    fragment = t.content.cloneNode(true)
    // Update attributes
    pr = fragment.firstElementChild
    pr.setAttribute("id"    , pr_data.uuid)
    pr.setAttribute("status", get_pr_status(pr_data))
    // Alg identifier 
    set_label( pr, 'alg-name'   , pr_data.identifier) 
    // Get the start-date label
    set_label( pr, 'start-date' , format_iso_date(pr_data.time_start))
    set_label( pr, 'finish-date', format_iso_date(pr_data.time_end))
    // Progress
    update_progressbar( pr, pr_data.percent_done )
    // Insert it
    let pr_list = document.getElementById("pr-list")
    pr_list.appendChild(fragment)
}

function update_process( pr_data ) {
    // Get our template
    let pr  = document.getElementById(pr_data.uuid)
    if (pr) {
        // Update attributes
        st = get_pr_status(pr_data)
        // status changed
        if (pr.getAttribute("status") != st) {
            pr.setAttribute("status", st)
            set_label( pr, 'finish-date', format_iso_date(pr_data.time_end))
            set_label( pr, 'start-date' , format_iso_date(pr_data.time_start))
        }
        // update progress bar
        update_progressbar( pr, pr_data.percent_done )
    } else {
        add_process( pr_data )
    }
}

function delete_process( uuid, dontask ) {
   let pr  = document.getElementById(uuid)
   if (pr && (dontask || doconfirm("Are you sure to delete these results ?"))) {
        pr.remove()
    }
}


function update_summary() {
   states = {
      'wait' : 0,
      'error': 0,
      'run': 0,
      'done' : 0
   }
   for( key of PROCESSES.keys()) {
        e = document.getElementById(key)
        states[e.getAttribute('status')] += 1
   }
   el = document.getElementById('pr-summary')
   for( k of ['wait','error','run','done']) {
        set_label(el, 'pr-'+k+'-count', states[k])
   }
}

function show_details( pr_data ) {
    for(let key in pr_data) {
        el = document.querySelector('#lbl-'+key)
        if (el) {
            let value = pr_data[key]
            let dtype = el.getAttribute("dtype")
            if (dtype == "date") {
                value = format_iso_date(value)
            }
            el.dataset.value = value 
        }
    }
}


async function get_status() {
    console.log("Refreshing status")
    let response = await fetch('/status/')
    if (! response.ok) {
        alert("Status response error")
        return
    }

    let data = await response.json();
    let newMap = new Map()
    for (pr_data of data['status']) {
         update_process(pr_data)
         newMap.set(pr_data.uuid,pr_data)
    } 
    // Clean up unreferenced data
    for (key of PROCESSES.keys()) {
        if (newMap.get(key) === undefined) {
            let pr = document.getElementById(key)
            if (pr)
                pr.remove()
        }
    }
    PROCESSES = newMap
    update_summary()
}


async function run_dashboard()
{
    await get_status()
    setInterval( get_status, 5000 )
}



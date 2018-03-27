
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
    return lbl
}

function update_progressbar( el, value ) {
    let progress = el.querySelector('[name=pr-progress] .progress-bar')
    progress.setAttribute('aria-valuenow', value )
    progress.style.width = value+'%'
}

function add_process( pr_data ) {
    // Get our template
    let t  = document.getElementById("pr-template")
    let fragment = t.content.cloneNode(true)
    // Update attributes
    let pr = fragment.firstElementChild
    pr.setAttribute("id"    , pr_data.uuid)
    pr.setAttribute("status", get_pr_status(pr_data))
    pr.setAttribute("title" , pr_data.message)
    // Alg identifier 
    let link = set_label( pr, 'alg-name', pr_data.identifier)
    link.setAttribute('href', 'details.html?uuid='+ pr_data.uuid)
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
            pr.setAttribute("title" , pr_data.message)
            set_label( pr, 'finish-date', format_iso_date(pr_data.time_end))
            set_label( pr, 'start-date' , format_iso_date(pr_data.time_start))
        }
        // update progress bar
        update_progressbar( pr, pr_data.percent_done )
    } else {
        add_process( pr_data )
    }
    $('[data-toggle="tooltip"]').tooltip();
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
   for(let key of PROCESSES.keys()) {
        e = document.getElementById(key)
        states[e.getAttribute('status')] += 1
   }
   el = document.getElementById('pr-summary')
   for(let k of ['wait','error','run','done']) {
        set_label(el, 'pr-'+k+'-count', states[k])
   }
}

function show_details( pr_data ) {
    document.getElementById('pr-raw-link').setAttribute('href','../status/' + pr_data.uuid)
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


/*
 * Details
 */

async function get_details_status(uuid) {
    console.log("Refreshing status: " + uuid)
    let response = await fetch('../status/' + uuid, { credentials: 'same-origin' })
    if (! response.ok) {
        return
    }    
    let pr_data = (await response.json())['status'];
    show_details(pr_data)
    refresh_store(pr_data.uuid)
    refresh_log(pr_data.uuid)
}


async function refresh_store( uuid ) {
    /* Update file list */
    $("#store-table tbody").empty()
    console.log("Refreshing store: " + uuid)
    let response = await fetch('../store/' + uuid + '/', { credentials: 'same-origin' })
    if (! response.ok) {
        return
    }
    data = await response.json()
    for (let res of data['files']) {
         insert_resource_details(res)
    }
}


function insert_resource_details( res ) {
    let t  = document.getElementById("tr-file-template")
    let fragment = t.content.cloneNode(true)
    // Update attributes
    let tr = fragment.firstElementChild
    set_label( tr, 'f-name', res.name).setAttribute('href', res.store_url)
    // Get the start-date label
    set_label( tr, 'f-type' , 'file')
    set_label( tr, 'f-size' , res.display_size)
    // Insert it
    document.getElementById("store-table-body").appendChild(fragment)
}


async function refresh_log( uuid ) {
    console.log("Refreshing log: " + uuid)
    let response = await fetch('../store/' + uuid + '/processing.log', { credentials: 'same-origin' })
    if (! response.ok) {
        return
    }
    let data = await response.text()
    el = document.getElementById('pane-log')
    set_label( el, 'log-content' , data )
}


async function refresh_details() {
    let params = (new URL(document.location)).searchParams;
    let uuid   = params.get('uuid')
    await get_details_status(uuid)
}



/*
 * Dashboard
 */

async function get_status() {
    console.log("Refreshing status")
    let response = await fetch('../status/', { credentials: 'same-origin' })
    if (! response.ok) {
        return
    }

    let data = await response.json();
    let newMap = new Map()
    for (let pr_data of data['status']) {
         update_process(pr_data)
         newMap.set(pr_data.uuid,pr_data)
    } 
    // Clean up unreferenced data
    for (let key of PROCESSES.keys()) {
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

/*
 * Bootstrap Init stuff
 */
$(document).ready(function(){
    $('[data-toggle="tooltip"]').tooltip();
});


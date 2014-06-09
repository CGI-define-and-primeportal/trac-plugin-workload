$(document).ready(function() {

  var spinner_markup = "<i class='workload-spinner icon-spinner \
                        icon-spin icon-2x color-muted-dark'></i>"
  var workload_selectors = "#milestone-workload, #milestone-workload-hours, \
                            #milestone-workdone, #milestone-workdone-hours"
  $(workload_selectors).append(spinner_markup);

  var other_workload_ticket_query = '';
  var other_workload_hours_query = '';
  var other_workdone_ticket_query = '';
  var other_workdone_hours_query = '';

  $.ajax({
    type:"GET",
    data: {'id': milestone_name},
    url: window.tracBaseUrl + "ajax/workload",
    success: function(data) {
      $(".workload-spinner").remove();

      // render the piecharts
      draw_piechart(data['remaining_tickets'], 'milestone-workload');
      draw_piechart(data['remaining_hours'], 'milestone-workload-hours');
      draw_piechart(data['closed_tickets'], 'milestone-workdone');
      draw_piechart(data['logged_hours'], 'milestone-workdone-hours');

      // update other query variables for later use in hyperlinks
      other_workload_ticket_query = data['remaing_tickets_other'];
      other_workload_hours_query = data['remaining_hours_other'];
      other_workdone_ticket_query = data['closed_tickets_other'];
      other_workdone_hours_query = data['logged_hours_other'];

    },
    error: function(data) {
      $(".workload-spinner, #milestone-workload-hours, #milestone-workdone-hours").remove()
      $("#milestone-workdone, #milestone-workload").removeClass("span6 center")
                                                   .addClass("span12")
                                                   .html("<i class='icon-info-sign'></i> Failed to retrieve workload data.")
    }
  });

  function draw_piechart(data, chart) {
    var plot1 = jQuery.jqplot (chart, [data], 
      { 
        seriesDefaults: {
          renderer: jQuery.jqplot.PieRenderer, 
          rendererOptions: {
            showDataLabels: true,
            dataLabels: 'value', // can use 'percent' too
            shadowAlpha: 0,
            dataLabelFormatString: (chart == 'milestone-workload' || chart == 'milestone-workdone') ? null : '%.2f'
          }
        }, 
        legend: { show:true, location: 'e' },
        grid: {
          background: "#F5F5F5",
          shadow: false,
          borderWidth: 0
        },
        seriesColors: [ "#23932C", "#dbb800", "#A94442", "#e9ba9e", "#CEF5D1",
                        "#9966FF", "#ab8800", "#DFEEFD", "#80ff80", "#F2DEDE"]
      }
    );
  };

  // set the correct title attribute when user hovers over segment
  $(workload_selectors).bind('jqplotDataHighlight', function(ev, seriesIndex, pointIndex, data) {
    var $this = $(this);
    $this.css('cursor', 'pointer');
    title = data[0] + ": " + data[1]
    if ($this.attr('id') == "milestone-workload") {
      $this.attr('title', title + " open tickets");
    }
    else if ($this.attr('id') == "milestone-workload-hours") {
      $this.attr('title', title + " hours remaining");
    }
    else if ($this.attr('id') == "milestone-workdone") {
      $this.attr('title', title + " tickets closed");
    }
    else if ($this.attr('id') == "milestone-workdone-hours") {
      $this.attr('title', title + " hours logged");
    }
    else {
      $this.attr('title', title);
    }
  });

  // remove title attribute on mouseout
  $(workload_selectors).bind('jqplotDataUnhighlight', function(ev, seriesIndex, pointIndex, data) {
    var $this = $(this);
    $this.attr('title',""); 
  });

  // set link when user clicks on segment
  $(workload_selectors).bind('  jqplotDataClick', function(ev, seriesIndex, pointIndex, data) {
    if (data[0] == "unassigned") {
      var query = "query?owner=&milestone=" + milestone_name;
    } 
    else if (data[0] == "other") {
      var query = other_query_sting($(this).attr('id'));
    } else {
      var query = "query?owner=~" + data[0] + "&milestone=" + milestone_name;
    }

    if ($(this).attr('id') == "milestone-workdone") {
      var query = query + "&status=closed";
    }
    else if ($(this).attr('id') == "milestone-workdone-hours") {
      // send user to manage hours page if they click on the hours logged chart
      var query = "hours?col=seconds_worked&col=worker&col=time_started&worker_filter=" + data[0];
    }
    else {
      var query = query + "&status=!closed";
    }
    window.location = (window.tracBaseUrl + query)
  });

  function other_query_sting(element_id) {
    if (element_id == 'milestone-workload') {
      var exclude = other_workload_ticket_query;
    }
    else if (element_id == 'milestone-workload-hours') {
      var exclude = other_workload_hours_query;
    }
    else if (element_id == 'milestone-workdone') {
      var exclude = other_workdone_ticket_query;
    }
    else if (element_id == 'milestone-workdone-hours') {
      var exclude = other_workdone_hours_query;
    }

    return "query?" + exclude + "&milestone=" + milestone_name;

  }


})
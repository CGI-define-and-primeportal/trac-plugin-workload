$(document).ready(function() {

  var spinner_markup = "<i class='workload-spinner icon-spinner \
                        icon-spin icon-2x color-muted-dark'></i>"
  var workload_selectors = "#milestone-workload, #milestone-workload-hours, \
                            #milestone-workdone, #milestone-workdone-hours"
  $(workload_selectors).append(spinner_markup);

  $.ajax({
    type:"GET",
    data: {'id': milestone_name},
    url: window.tracBaseUrl + "ajax/workload",
    success: function(data) {
      $(".workload-spinner").remove();
      draw_piechart(data[0], 'milestone-workload');
      draw_piechart(data[1], 'milestone-workload-hours');
      draw_piechart(data[2], 'milestone-workdone');
      draw_piechart(data[3], 'milestone-workdone-hours');
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
      var query = "/project1/query?owner=&milestone=" + milestone_name;
    } else {
      var query = "/project1/query?owner=~" + data[0] + "&milestone=" + milestone_name;
    }

    if ($(this).attr('id') == "milestone-workdone") {
      var query = query + "&status=closed";
    }
    else if ($(this).attr('id') == "milestone-workdone-hours") {
      // send user to manage hours page if they click on the hours logged chart
      var query = "/project1/hours?col=seconds_worked&col=worker&col=time_started&worker_filter=" + data[0];
    }
    else {
      var query = query + "&status=!closed";
    }
    window.location = (query)
  });


})
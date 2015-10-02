from trac.config import Option
from trac.core import Component, TracError, implements
from trac.resource import ResourceNotFound
from trac.ticket.model import Milestone
from trac.util.presentation import to_json, DecimalEncoder
from trac.web import ITemplateStreamFilter
from trac.web.api import IRequestHandler
from trac.web.chrome import ITemplateProvider, add_script, add_stylesheet, add_script_data

from genshi.filters.transform import Transformer
from genshi.builder import tag
import pkg_resources
import re

class Workload(Component):

    implements(IRequestHandler, ITemplateStreamFilter, ITemplateProvider)

    user_limit = Option('workload', 'workload_user_limit', 9)

    # IRequestHandler methods

    def match_request(self, req):
        """
        Match requests to ajax/workload. We don't check the validity of 
        the milestone as this would involve a database query which would 
        slow the request cycle down significantly.
        """

        return req.path_info.startswith("/ajax/workload")

    def process_request(self, req):
        """
        Send a JSON response containing workload data to a XMLHttpRequest. Any 
        other type of request raise a TracError.
        """

        if not req.get_header('X-Requested-With') == 'XMLHttpRequest':
            raise TracError("We only accept XMLHttpRequests to this URL")

        milestone = self._get_milestone(req.args['id'])

        if milestone:
            closed_count = self._limit_user_data(self._get_closed_ticket_count(milestone.name))
            logged_count = self._limit_user_data(self._get_hours_logged(milestone.name))
            data = {
                'closed_tickets': self._limit_user_data(closed_count),
                'closed_tickets_other': self._other_user_query_string(closed_count),
                'logged_hours': self._limit_user_data(logged_count),
                'logged_hours_other': self._other_user_query_string(logged_count),
            }

            if milestone.completed:
                data['milestone_completed'] =  True
            else:
                ticket_count = self._limit_user_data(self._get_open_ticket_count(milestone.name))
                hour_count = self._limit_user_data(self._get_remaining_hours(milestone.name))
                data.update({
                    'milestone_completed': False,
                    'remaining_tickets': self._limit_user_data(ticket_count),
                    'remaing_tickets_other': self._other_user_query_string(ticket_count),
                    'remaining_hours': self._limit_user_data(hour_count),
                    'remaining_hours_other': self._other_user_query_string(hour_count),
                })
        else:
            data = {}

        req.send(to_json(data, cls=DecimalEncoder), 'text/json')

    # ITemplateStreamFilter method

    def filter_stream(self, req, method, filename, stream, data):
        """
        We add JavaScript files and other DOM elements via the filter stream, 
        but actually query the DB and parse the data after the initial page 
        load via AJAX for a page load performance boost. See IRequestHandler 
        methods.

        We only add these scripts and elements if the milestone has a minimum 
        of atleast one ticket.

        We also only render the completed work DOM elements if a minimum of 
        one ticket has been closed.
        """

        if req.path_info.startswith('/milestone/'):

            milestone = self._get_milestone(req.args['id'])
            if milestone and self._milestone_has_ticket(milestone.name):

                add_script(req, 'common/js/jqPlot/jquery.jqplot.js')
                add_script(req, 'common/js/jqPlot/excanvas.min.js')
                add_script(req, 'common/js/jqPlot/plugins/jqplot.pieRenderer.min.js')
                add_stylesheet(req, 'common/js/jqPlot/jquery.jqplot.css')
                add_stylesheet(req, 'workload/css/workload.css')
                add_script(req, 'workload/js/workload.js')
                add_script_data(req, {'milestone_name': milestone.name})

                if not milestone.completed:
                    workload_tag = tag(
                        tag.h2("Remaining Work ", class_="inline-block"),
                        tag.i(id_='workload-help',class_='fa fa-question-circle color-muted'),
                        tag.div(
                            tag.div(id_='milestone-workload',
                                    class_='milestone-info span6 center',
                                    style="display:inline;"
                            ),
                            tag.div(id_='milestone-workload-hours',
                                    class_='milestone-info span6 center',
                                    style="display:inline;"
                            ),
                        id_="workload-charts",
                        class_="row-fluid"
                        ),
                        tag.div(
                            tag.p("Remaining work pie charts are generated to help projects recognise the effort necessary to complete the milestone."),
                            tag.p("The open tickets chart counts the number of open tickets each project member has to complete within the milestone."),
                            tag.p("The remaining hours chart reflects the cumulative estimated hours of efforts required to close these tickets."),
                            tag.p("In both charts only the top {0} members with the highest ticket/hours count are displayed. Remaining members have their data aggregated into a 'other' group.".format(self.user_limit)),
                            id_="workload-dialog", class_="hidden"
                        ),
                    )
                    stream = stream | Transformer("//*[@id='field-analysis']").after(workload_tag)

                if self._milestone_has_closed_ticket(milestone.name):

                    workdone_tag = tag(
                        tag.h2("Completed Work ", class_="inline-block"),
                        tag.i(id_='workdone-help', class_='fa fa-question-circle color-muted'),
                        tag.div(
                            tag.div(id_='milestone-workdone',
                                    class_='milestone-info span6 center',
                                    style="display:inline;"
                            ),
                            tag.div(id_='milestone-workdone-hours',
                                    class_='milestone-info span6 center',
                                    style="display:inline;"
                            ),
                        id_="workdone-charts",
                        class_="row-fluid"
                        ),
                        tag.div(
                            tag.p("Completed work pie charts are generated to help projects analyse the contribution of members during the milestone."),
                            tag.p("The closed tickets charts counts the number of tickets each project member has completed during the milestone."),
                            tag.p("The hours logged chart reflects the cumulative hours of work that were required to close these tickets."),
                            tag.p("In both charts only the top {0} members with the highest ticket/hours count are displayed. Remaining members have their data aggregated into a 'other' group.".format(self.user_limit)),
                            id_="workdone-dialog", class_="hidden"
                        ),
                    )

                    div = 'workload-charts' if not milestone.completed else 'field-analysis'
                    stream = stream | Transformer("//*[@id='{0}']".format(div)).after(workdone_tag)

        return stream

    # ITemplateProvider methods

    def get_htdocs_dirs(self):
        return [('workload', pkg_resources.resource_filename(__name__,
                                                                'htdocs'))]

    def get_templates_dirs(self):
        return [pkg_resources.resource_filename(__name__, 'templates')]

    # Private methods

    def _get_milestone(self, milestone):
        """Returns a milestone instance if one exists, or None if it
        does not."""

        try:
            m = Milestone(self.env, milestone)
        except ResourceNotFound:
            m = None
        return m

    def _milestone_has_ticket(self, milestone):
        db = self.env.get_read_db()
        cursor = db.cursor()
        cursor.execute("""SELECT id FROM ticket 
                          WHERE milestone=%s
                          LIMIT 1""",
                          (milestone,))
        return cursor.fetchone()

    def _milestone_has_closed_ticket(self, milestone):
        db = self.env.get_read_db()
        cursor = db.cursor()
        cursor.execute("""SELECT id FROM ticket 
                          WHERE milestone=%s
                            AND status = 'closed'
                          LIMIT 1""",
                          (milestone,))
        return cursor.fetchone()

    def _get_open_ticket_count(self, milestone):
        db = self.env.get_read_db()
        cursor = db.cursor()
        cursor.execute("""SELECT owner, COUNT(*)
                          FROM ticket 
                          WHERE milestone=%s
                            AND status != 'closed'
                          GROUP BY owner
                          ORDER BY COUNT(*) DESC""",
                          (milestone,))
        return cursor.fetchall()

    def _get_remaining_hours(self, milestone):
        db = self.env.get_read_db()
        cursor = db.cursor()
        # can't cast as int due to decimal remaininghours values
        cursor.execute("""SELECT t.owner, SUM(CAST(c.value as numeric))
                        FROM ticket as t
                        JOIN ticket_custom AS c
                            ON c.ticket = t.id
                        WHERE t.milestone=%s
                            AND c.name=%s
                            AND t.status!='closed'
                            AND CAST(c.value as numeric)>0
                        GROUP BY t.owner
                        ORDER BY SUM(CAST(c.value as numeric)) DESC""",
                  (milestone,"remaininghours"))
        return cursor.fetchall()

    def _get_closed_ticket_count(self, milestone):
        db = self.env.get_read_db()
        cursor = db.cursor()
        cursor.execute("""SELECT owner, COUNT(*) FROM ticket 
                          WHERE milestone=%s
                            AND status = 'closed'
                          GROUP BY owner
                          ORDER BY COUNT(*) DESC""",
                          (milestone,))
        return cursor.fetchall()

    def _get_hours_logged(self, milestone):
        db = self.env.get_read_db()
        cursor = db.cursor()
        cursor.execute("""SELECT tt.worker, SUM(tt.seconds_worked) 
                          FROM ticket_time as tt 
                          JOIN ticket as t
                            ON t.id = tt.ticket
                          WHERE t.milestone=%s
                          GROUP BY tt.worker
                          ORDER BY SUM(tt.seconds_worked) DESC""",
                          (milestone,))

        return [(worker, (logged/60/60)) for worker, logged in cursor]

    def _limit_user_data(self, data, limit=None):
        """Summarises user data to limit the number of individual users 
        referenced. This is mainly a convience to keep the UI nice and tidy.

        By default this uses the limit values set by the self.user_limit 
        config option.

        Unassigned tickets have a empty string value in the ticket table, 
        so we find this tuple if present and change the label to 'unassigned.
        """

        data = [(owner, work) if owner else ('unassigned', work)
                              for owner, work in data]

        if limit is None:
            limit = self.user_limit

        if len(data) > limit:
            other = [('other', sum(i[1] for i in data[limit:]))]
        else:
            other = []

        return data[:limit] + other

    def _other_user_query_string(self, data):
        """
        Returns a query string we can use to form a ticket query hyperlink 
        which omits all of the named users within the data. This is necessary 
        for the 'other' piechart link generated by our JavaScript.

        For example [('danny', 5), ('adam', 3), ('other', 2)] would return 
        owner=!danny&owner!=adam

        If the list does not include a tuple with a string 'other' we return 
        an empty string.

        Note that in _limit_user_data() we use a unassigned label to make data 
        more readable to end users - however in the query string we must an 
        empty string to detect unassigned tickets - hence replace().
        """

        if 'other' in (t[0] for t in data):
            return "owner=!" + "&owner=!".join(t[0] for t in data if t[0] != 'other').replace('unassigned', '')
        else:
            return ""

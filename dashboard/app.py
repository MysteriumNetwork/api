from flask import Flask, render_template
from dashboard import model_layer
from werkzeug.contrib.cache import SimpleCache
from dashboard.helpers import get_week_range
from datetime import datetime
import settings

app = Flask(__name__)
model_layer.get_db().init_app(app)

cache = SimpleCache()

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://{}:{}@{}/{}'.format(
    settings.USER, settings.PASSWD, settings.DB_HOST, settings.DB_NAME)


@app.route('/')
def main():
    page_content = cache.get('dashboard-page')
    if page_content is None:

        page_content = render_template(
            'dashboard.html',
            active_nodes_count=model_layer.get_active_nodes_count(),
            sessions_count=model_layer.get_sessions_count(),
            active_sessions_count=model_layer.get_sessions_count(
                only_active_sessions=True
            ),
            average_session_time=model_layer.get_average_session_time(),
            total_data_transferred=model_layer.get_total_data_transferred(),
            available_nodes=model_layer.get_available_nodes(limit=10),
            sessions=model_layer.get_sessions(limit=10),
        )

        cache.set(
            'dashboard-page',
            page_content,
            timeout=1 * 60
        )

    return page_content


@app.route('/leaderboard')
def leaderboard():
    page_content = cache.get('leaderboard')
    if page_content is None:
        date_from, date_to = get_week_range(datetime.utcnow().date())
        nodes = model_layer.get_registered_nodes(date_from, date_to)
        model_layer.enrich_registered_nodes_info(nodes, date_from, date_to)
        page_content = render_template(
            'leaderboard.html',
            date_from=date_from.strftime("%Y-%m-%d"),
            date_to=date_to.strftime("%Y-%m-%d"),
            leaderboard_nodes=nodes,
        )
        cache.set(
            'leaderboard',
            page_content,
            timeout=1 * 60
        )

    return page_content


@app.route('/node/<key>/<service_type>')
def node(key, service_type):
    node = model_layer.get_node_info(key, service_type)
    return render_template(
        'node.html',
        node=node,
    )


@app.route('/nodes')
def nodes():

    nodes = cache.get('all-nodes')
    if nodes is None:
        nodes = model_layer.get_nodes(limit=500)
        cache.set(
            'all-nodes',
            nodes,
            timeout=1 * 60
        )

    return render_template(
        'nodes.html',
        nodes=nodes
    )


@app.route('/session/<key>')
def session(key):
    session = model_layer.get_session_info(key)
    return render_template(
        'session.html',
        session=session,
    )


@app.route('/sessions')
def sessions():
    sessions = cache.get('all-sessions')
    if sessions is None:
        sessions = model_layer.get_sessions(limit=500)
        cache.set(
            'all-sessions',
            sessions,
            timeout=1 * 60
        )

    return render_template(
        'sessions.html',
        sessions=sessions
    )


@app.route('/sessions-country')
def sessions_country():
    results = model_layer.get_sessions_country_stats()

    return render_template(
        'sessions-country.html',
        stats=results
    )


if __name__ == '__main__':
    app.run(debug=True)

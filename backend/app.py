from flask import Flask, request, jsonify, send_from_directory
import requests
from flask_cors import CORS
import os

app = Flask(__name__, static_folder='../frontend')
CORS(app)

# Put your TMDb key here (or set TMDB_API_KEY env var)
TMDB_API_KEY = "14af6eccd4684260446f9db68bf0ce86"


def tmdb_get(url, params=None):
    """Helper: call TMDb with api_key and return (data, error)"""
    if params is None:
        params = {}
    params['api_key'] = TMDB_API_KEY
    try:
        resp = requests.get(url, params=params, timeout=10)
    except requests.RequestException as e:
        app.logger.error("Network error calling TMDb: %s", e)
        return None, {"error": "Network error contacting TMDb", "detail": str(e)}
    try:
        data = resp.json()
    except ValueError:
        app.logger.error("Non-JSON response from TMDb: %s", resp.text)
        return None, {"error": "Invalid response from TMDb", "status_code": resp.status_code, "text": resp.text}
    if resp.status_code != 200:
        app.logger.error("TMDb returned error %s: %s", resp.status_code, data)
        return None, {"error": data.get("status_message", "TMDb error"), "status_code": resp.status_code}
    return data, None


@app.route('/search')
def search():
    movie_name = request.args.get('q')
    country = request.args.get('country', 'US')
    if not movie_name:
        return jsonify({'error': 'No movie name provided'}), 400

    search_url = "https://api.themoviedb.org/3/search/movie"
    search_data, err = tmdb_get(search_url, params={"query": movie_name})
    if err:
        return jsonify({"error": "TMDb search failed", "detail": err}), 502

    results = []
    for movie in search_data.get("results", [])[:5]:
        movie_id = movie["id"]

        provider_url = f"https://api.themoviedb.org/3/movie/{movie_id}/watch/providers"
        provider_data, perr = tmdb_get(provider_url)
        providers = []
        link = None
        if not perr and country in provider_data.get("results", {}):
            country_data = provider_data["results"][country]
            link = country_data.get("link")
            for prov in country_data.get("flatrate", []):
                providers.append(prov.get("provider_name"))

        results.append({
            "title": movie.get("title"),
            "year": (movie.get("release_date") or "")[:4],
            "poster": f"https://image.tmdb.org/t/p/w200{movie['poster_path']}" if movie.get("poster_path") else None,
            "providers": providers,
            "link": link
        })

    return jsonify(results)


@app.route('/trending')
def trending():
    country = request.args.get('country', 'US')

    trending_url = "https://api.themoviedb.org/3/trending/movie/week"
    trending_data, err = tmdb_get(trending_url)
    if err:
        return jsonify({"error": "TMDb trending failed", "detail": err}), 502

    results = []
    for movie in trending_data.get("results", [])[:10]:
        movie_id = movie["id"]
        provider_url = f"https://api.themoviedb.org/3/movie/{movie_id}/watch/providers"
        provider_data, perr = tmdb_get(provider_url)

        providers = []
        link = None
        if not perr and country in provider_data.get("results", {}):
            country_data = provider_data["results"][country]
            link = country_data.get("link")
            for prov in country_data.get("flatrate", []):
                providers.append(prov.get("provider_name"))

        results.append({
            "title": movie.get("title"),
            "year": (movie.get("release_date") or "")[:4],
            "poster": f"https://image.tmdb.org/t/p/w200{movie['poster_path']}" if movie.get("poster_path") else None,
            "providers": providers,
            "link": link
        })

    return jsonify(results)


# Serve frontend static files
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder, path)


if __name__ == '__main__':
    # Start server (make sure all routes are defined BEFORE this line)
    app.run(debug=True, port=5000)

from flask import Flask, redirect, request, session, url_for, render_template
import requests
import base64

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Cambia esto a una clave más segura en producción

# Configuración
CLIENT_ID = '71a4864d55fd48d3bf5153b1e596ca01'
CLIENT_SECRET = '63a715c246674947be730b392bc18b86'
REDIRECT_URI = 'http://127.0.0.1:5000/callback'
SCOPE = 'user-library-read user-top-read playlist-modify-public'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    auth_url = (
        f'https://accounts.spotify.com/authorize?response_type=code&'
        f'client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={SCOPE}'
    )
    return redirect(auth_url)


@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return 'No authorization code provided', 400

    token_url = 'https://accounts.spotify.com/api/token'
    auth_header = base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode()).decode()
    
    response = requests.post(
        token_url,
        headers={
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI
        }
    )
    
    if response.status_code != 200:
        return f'Error getting access token: {response.text}', 500
    
    response_data = response.json()
    session['access_token'] = response_data.get('access_token')
    if not session['access_token']:
        return 'Failed to retrieve access token', 500

    return redirect(url_for('discover'))

@app.route('/discover')
def discover():
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('login'))

    top_tracks_url = 'https://api.spotify.com/v1/me/top/tracks'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    top_tracks_response = requests.get(top_tracks_url, headers=headers)
    if top_tracks_response.status_code != 200:
        return f'Error fetching top tracks: {top_tracks_response.text}', 500
    
    top_tracks_data = top_tracks_response.json()
    track_ids = [track['id'] for track in top_tracks_data['items']]

    if not track_ids:
        return 'No top tracks found to seed recommendations', 500

    recommendations_url = 'https://api.spotify.com/v1/recommendations'
    recommendations_params = {
        'seed_tracks': ','.join(track_ids[:5])
    }
    
    recommendations_response = requests.get(
        recommendations_url,
        headers=headers,
        params=recommendations_params
    )
    
    if recommendations_response.status_code != 200:
        return f'Error fetching recommendations: {recommendations_response.text}', 500
    
    recommendations_data = recommendations_response.json()
    recommended_tracks = recommendations_data['tracks']
    
    create_playlist_url = 'https://api.spotify.com/v1/me/playlists'
    playlist_data = {
        'name': 'Discover Playlist',
        'description': 'Playlist with new music recommendations.',
        'public': True
    }
    
    create_playlist_response = requests.post(
        create_playlist_url,
        headers=headers,
        json=playlist_data
    )
    
    if create_playlist_response.status_code != 201:
        return f'Error creating playlist: {create_playlist_response.text}', 500
    
    playlist_data = create_playlist_response.json()
    playlist_id = playlist_data['id']
    
    add_tracks_url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
    track_uris = [track['uri'] for track in recommended_tracks]
    
    add_tracks_response = requests.post(
        add_tracks_url,
        headers=headers,
        json={'uris': track_uris}
    )
    
    if add_tracks_response.status_code == 201:
        playlist_url = f'https://open.spotify.com/playlist/{playlist_id}'
        return render_template('success.html', playlist_url=playlist_url)
    else:
        return f'Error adding tracks to playlist: {add_tracks_response.text}', add_tracks_response.status_code

if __name__ == '__main__':
    app.run(port=5000)

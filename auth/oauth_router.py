"""OAuth router for social authentication"""
import secrets
import asyncio
from aiohttp import web, web_response
from aiohttp_session import get_session
import aiohttp_cors
from typing import Dict, Any
import jwt
import os
from datetime import datetime, timedelta

from .oauth import oauth_manager
from users.database import get_user_by_email, create_user, User
from .login.database import create_access_token


async def oauth_login(request: web.Request):
    """Start OAuth login flow"""
    provider = request.match_info['provider']
    
    # Check if provider is available
    if provider not in oauth_manager.get_available_providers():
        return web.json_response({
            'error': f'Provider {provider} not configured or available',
            'available_providers': oauth_manager.get_available_providers()
        }, status=400)
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Store state in session
    session = await get_session(request)
    session['oauth_state'] = state
    session['oauth_provider'] = provider
    
    try:
        # Get authorization URL
        authorization_url = await oauth_manager.get_authorization_url(provider, state)
        
        return web.json_response({
            'authorization_url': authorization_url,
            'state': state
        })
    
    except Exception as e:
        return web.json_response({
            'error': f'Failed to get authorization URL: {str(e)}'
        }, status=500)


async def oauth_callback(request: web.Request):
    """Handle OAuth callback"""
    provider = request.match_info['provider']
    query = request.query
    
    # Get session
    session = await get_session(request)
    stored_state = session.get('oauth_state')
    stored_provider = session.get('oauth_provider')
    
    # Verify state for CSRF protection
    received_state = query.get('state')
    if not stored_state or stored_state != received_state:
        return web.json_response({
            'error': 'Invalid state parameter. Possible CSRF attack.'
        }, status=400)
    
    # Verify provider matches
    if stored_provider != provider:
        return web.json_response({
            'error': 'Provider mismatch'
        }, status=400)
    
    # Check for error in callback
    if 'error' in query:
        error_description = query.get('error_description', 'Unknown error')
        return web.json_response({
            'error': f'OAuth error: {error_description}'
        }, status=400)
    
    # Get authorization code
    code = query.get('code')
    if not code:
        return web.json_response({
            'error': 'Authorization code not provided'
        }, status=400)
    
    try:
        # Exchange code for user information
        user_info = await oauth_manager.get_user_info(provider, code)
        
        if not user_info.get('email'):
            return web.json_response({
                'error': 'Email not provided by OAuth provider'
            }, status=400)
        
        # Check if user exists
        existing_user = await get_user_by_email(user_info['email'])
        
        if existing_user:
            # User exists, log them in
            user = existing_user
            
            # Update user info from OAuth if needed
            update_data = {}
            if not user.first_name and user_info.get('first_name'):
                update_data['first_name'] = user_info['first_name']
            if not user.last_name and user_info.get('last_name'):
                update_data['last_name'] = user_info['last_name']
            if user_info.get('picture') and user_info['picture'] != user.avatar_url:
                update_data['avatar_url'] = user_info['picture']
            
            # Update OAuth provider info
            oauth_providers = user.oauth_providers or {}
            oauth_providers[provider] = {
                'id': user_info['id'],
                'connected_at': datetime.utcnow().isoformat()
            }
            update_data['oauth_providers'] = oauth_providers
            
            if update_data:
                # Update user in database
                from users.database import update_user
                await update_user(user.id, **update_data)
        
        else:
            # Create new user
            user_data = {
                'email': user_info['email'],
                'first_name': user_info.get('first_name', ''),
                'last_name': user_info.get('last_name', ''),
                'username': user_info.get('name', user_info['email'].split('@')[0]),
                'avatar_url': user_info.get('picture'),
                'is_active': True,
                'oauth_providers': {
                    provider: {
                        'id': user_info['id'],
                        'connected_at': datetime.utcnow().isoformat()
                    }
                }
            }
            
            try:
                user = await create_user(**user_data)
            except Exception as e:
                return web.json_response({
                    'error': f'Failed to create user: {str(e)}'
                }, status=500)
        
        # Create access token
        access_token = create_access_token(user.id)
        
        # Clear OAuth session data
        session.pop('oauth_state', None)
        session.pop('oauth_provider', None)
        
        # Return success response with redirect to frontend
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:8001')
        redirect_url = f"{frontend_url}/dashboard.html?token={access_token}"
        
        # For web callback, redirect to frontend
        if request.headers.get('Accept', '').startswith('text/html'):
            return web_response.Response(
                text=f"""
                <html>
                <head>
                    <title>Login Successful</title>
                    <style>
                        body {{
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
                            background: linear-gradient(135deg, #0d1117, #161b22);
                            color: #f0f6fc;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            height: 100vh;
                            margin: 0;
                        }}
                        .container {{
                            text-align: center;
                            padding: 2rem;
                            border-radius: 12px;
                            background: rgba(22, 27, 34, 0.8);
                            border: 1px solid #30363d;
                        }}
                        .spinner {{
                            border: 3px solid #30363d;
                            border-top: 3px solid #238636;
                            border-radius: 50%;
                            width: 40px;
                            height: 40px;
                            animation: spin 1s linear infinite;
                            margin: 20px auto;
                        }}
                        @keyframes spin {{
                            0% {{ transform: rotate(0deg); }}
                            100% {{ transform: rotate(360deg); }}
                        }}
                    </style>
                    <script>
                        // Store token and redirect
                        localStorage.setItem('access_token', '{access_token}');
                        setTimeout(() => {{
                            window.location.href = '/dashboard.html';
                        }}, 2000);
                    </script>
                </head>
                <body>
                    <div class="container">
                        <h2>✅ Login Successful!</h2>
                        <div class="spinner"></div>
                        <p>Redirecting to dashboard...</p>
                    </div>
                </body>
                </html>
                """,
                content_type='text/html'
            )
        
        # For API callback, return JSON
        return web.json_response({
            'success': True,
            'access_token': access_token,
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'avatar_url': user.avatar_url
            },
            'redirect_url': redirect_url
        })
    
    except Exception as e:
        # Clear OAuth session data on error
        session.pop('oauth_state', None)
        session.pop('oauth_provider', None)
        
        return web.json_response({
            'error': f'OAuth authentication failed: {str(e)}'
        }, status=500)


async def get_oauth_providers(request: web.Request):
    """Get available OAuth providers"""
    providers = oauth_manager.get_available_providers()
    
    provider_info = {}
    for provider in providers:
        provider_info[provider] = {
            'name': provider.title(),
            'login_url': f'/auth/oauth/{provider}/login'
        }
    
    return web.json_response({
        'providers': provider_info
    })


async def disconnect_oauth_provider(request: web.Request):
    """Disconnect OAuth provider from user account"""
    provider = request.match_info['provider']
    
    # Get current user from JWT
    from .login.database import get_current_user
    try:
        user = await get_current_user(request)
        if not user:
            return web.json_response({'error': 'Authentication required'}, status=401)
    except Exception:
        return web.json_response({'error': 'Invalid token'}, status=401)
    
    # Check if user has OAuth providers
    oauth_providers = user.oauth_providers or {}
    
    if provider not in oauth_providers:
        return web.json_response({
            'error': f'Provider {provider} is not connected'
        }, status=400)
    
    # Remove the provider
    oauth_providers.pop(provider)
    
    # Update user
    from users.database import update_user
    await update_user(user.id, oauth_providers=oauth_providers)
    
    return web.json_response({
        'message': f'Successfully disconnected {provider}',
        'remaining_providers': list(oauth_providers.keys())
    })


# Create OAuth routes table
oauth_routes = web.RouteTableDef()

oauth_routes.get('/auth/oauth/providers')(get_oauth_providers)
oauth_routes.get('/auth/oauth/{provider}/login')(oauth_login)
oauth_routes.get('/auth/oauth/{provider}/callback')(oauth_callback)
oauth_routes.delete('/auth/oauth/{provider}/disconnect')(disconnect_oauth_provider)


def setup_oauth_routes(app: web.Application):
    """Setup OAuth routes (legacy function for backward compatibility)"""
    
    # OAuth routes
    app.router.add_get('/auth/oauth/providers', get_oauth_providers)
    app.router.add_get('/auth/oauth/{provider}/login', oauth_login)
    app.router.add_get('/auth/oauth/{provider}/callback', oauth_callback)
    app.router.add_delete('/auth/oauth/{provider}/disconnect', disconnect_oauth_provider)
    
    # Add CORS support
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        )
    })
    
    # Add CORS to all OAuth routes
    for route in app.router.routes():
        if route.resource and route.resource.canonical.startswith('/auth/oauth'):
            cors.add(route) 
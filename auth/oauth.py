"""OAuth configuration and providers for social authentication"""
import asyncio
import aiohttp
import json
from typing import Dict, Optional, Any
from aioauth_client import GoogleClient, FacebookClient, GithubClient
from authlib.integrations.base_client import *
import os


class OAuthProvider:
    """Base OAuth provider class"""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
    
    async def get_authorization_url(self) -> str:
        """Get authorization URL for OAuth flow"""
        raise NotImplementedError
    
    async def get_user_info(self, code: str) -> Dict[str, Any]:
        """Exchange code for user information"""
        raise NotImplementedError


class GoogleOAuthProvider(OAuthProvider):
    """Google OAuth provider"""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        super().__init__(client_id, client_secret, redirect_uri)
        self.scope = 'openid email profile'
    
    async def get_authorization_url(self, state: str) -> str:
        """Get Google authorization URL"""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': self.scope,
            'response_type': 'code',
            'access_type': 'offline',
            'state': state
        }
        
        param_string = '&'.join([f'{k}={v}' for k, v in params.items()])
        return f'https://accounts.google.com/o/oauth2/auth?{param_string}'
    
    async def get_user_info(self, code: str) -> Dict[str, Any]:
        """Exchange code for Google user information"""
        async with aiohttp.ClientSession() as session:
            # Exchange code for access token
            token_url = 'https://oauth2.googleapis.com/token'
            token_data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'redirect_uri': self.redirect_uri,
                'code': code,
                'grant_type': 'authorization_code'
            }
            
            async with session.post(token_url, data=token_data) as token_response:
                token_result = await token_response.json()
                
                if 'access_token' not in token_result:
                    raise ValueError(f"Failed to get access token: {token_result}")
                
                access_token = token_result['access_token']
            
            # Get user information
            user_url = f'https://www.googleapis.com/oauth2/v2/userinfo?access_token={access_token}'
            async with session.get(user_url) as user_response:
                user_data = await user_response.json()
                
                return {
                    'id': user_data.get('id'),
                    'email': user_data.get('email'),
                    'name': user_data.get('name'),
                    'first_name': user_data.get('given_name'),
                    'last_name': user_data.get('family_name'),
                    'picture': user_data.get('picture'),
                    'provider': 'google'
                }


class FacebookOAuthProvider(OAuthProvider):
    """Facebook OAuth provider"""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        super().__init__(client_id, client_secret, redirect_uri)
        self.scope = 'email,public_profile'
    
    async def get_authorization_url(self, state: str) -> str:
        """Get Facebook authorization URL"""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': self.scope,
            'response_type': 'code',
            'state': state
        }
        
        param_string = '&'.join([f'{k}={v}' for k, v in params.items()])
        return f'https://www.facebook.com/v18.0/dialog/oauth?{param_string}'
    
    async def get_user_info(self, code: str) -> Dict[str, Any]:
        """Exchange code for Facebook user information"""
        async with aiohttp.ClientSession() as session:
            # Exchange code for access token
            token_url = 'https://graph.facebook.com/v18.0/oauth/access_token'
            token_params = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'redirect_uri': self.redirect_uri,
                'code': code
            }
            
            async with session.get(token_url, params=token_params) as token_response:
                token_result = await token_response.json()
                
                if 'access_token' not in token_result:
                    raise ValueError(f"Failed to get access token: {token_result}")
                
                access_token = token_result['access_token']
            
            # Get user information
            user_url = 'https://graph.facebook.com/v18.0/me'
            user_params = {
                'fields': 'id,name,email,first_name,last_name,picture',
                'access_token': access_token
            }
            
            async with session.get(user_url, params=user_params) as user_response:
                user_data = await user_response.json()
                
                return {
                    'id': user_data.get('id'),
                    'email': user_data.get('email'),
                    'name': user_data.get('name'),
                    'first_name': user_data.get('first_name'),
                    'last_name': user_data.get('last_name'),
                    'picture': user_data.get('picture', {}).get('data', {}).get('url'),
                    'provider': 'facebook'
                }


class GitHubOAuthProvider(OAuthProvider):
    """GitHub OAuth provider"""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        super().__init__(client_id, client_secret, redirect_uri)
        self.scope = 'user:email'
    
    async def get_authorization_url(self, state: str) -> str:
        """Get GitHub authorization URL"""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': self.scope,
            'state': state
        }
        
        param_string = '&'.join([f'{k}={v}' for k, v in params.items()])
        return f'https://github.com/login/oauth/authorize?{param_string}'
    
    async def get_user_info(self, code: str) -> Dict[str, Any]:
        """Exchange code for GitHub user information"""
        async with aiohttp.ClientSession() as session:
            # Exchange code for access token
            token_url = 'https://github.com/login/oauth/access_token'
            token_data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': code
            }
            headers = {'Accept': 'application/json'}
            
            async with session.post(token_url, data=token_data, headers=headers) as token_response:
                token_result = await token_response.json()
                
                if 'access_token' not in token_result:
                    raise ValueError(f"Failed to get access token: {token_result}")
                
                access_token = token_result['access_token']
            
            # Get user information
            user_url = 'https://api.github.com/user'
            auth_headers = {
                'Authorization': f'token {access_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            async with session.get(user_url, headers=auth_headers) as user_response:
                user_data = await user_response.json()
                
                # Get user email (might be private)
                email = user_data.get('email')
                if not email:
                    email_url = 'https://api.github.com/user/emails'
                    async with session.get(email_url, headers=auth_headers) as email_response:
                        emails = await email_response.json()
                        primary_email = next((e for e in emails if e.get('primary')), None)
                        email = primary_email.get('email') if primary_email else None
                
                return {
                    'id': str(user_data.get('id')),
                    'email': email,
                    'name': user_data.get('name') or user_data.get('login'),
                    'first_name': user_data.get('name', '').split(' ')[0] if user_data.get('name') else '',
                    'last_name': ' '.join(user_data.get('name', '').split(' ')[1:]) if user_data.get('name') and len(user_data.get('name', '').split(' ')) > 1 else '',
                    'picture': user_data.get('avatar_url'),
                    'provider': 'github'
                }


class OAuthManager:
    """OAuth manager for handling multiple providers"""
    
    def __init__(self):
        self.providers = {}
        self._setup_providers()
    
    def _setup_providers(self):
        """Setup OAuth providers from environment variables"""
        # Google OAuth
        google_client_id = os.getenv('GOOGLE_CLIENT_ID')
        google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        google_redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8000/auth/oauth/google/callback')
        
        if google_client_id and google_client_secret:
            self.providers['google'] = GoogleOAuthProvider(
                google_client_id,
                google_client_secret,
                google_redirect_uri
            )
        
        # Facebook OAuth
        facebook_client_id = os.getenv('FACEBOOK_CLIENT_ID')
        facebook_client_secret = os.getenv('FACEBOOK_CLIENT_SECRET')
        facebook_redirect_uri = os.getenv('FACEBOOK_REDIRECT_URI', 'http://localhost:8000/auth/oauth/facebook/callback')
        
        if facebook_client_id and facebook_client_secret:
            self.providers['facebook'] = FacebookOAuthProvider(
                facebook_client_id,
                facebook_client_secret,
                facebook_redirect_uri
            )
        
        # GitHub OAuth
        github_client_id = os.getenv('GITHUB_CLIENT_ID')
        github_client_secret = os.getenv('GITHUB_CLIENT_SECRET')
        github_redirect_uri = os.getenv('GITHUB_REDIRECT_URI', 'http://localhost:8000/auth/oauth/github/callback')
        
        if github_client_id and github_client_secret:
            self.providers['github'] = GitHubOAuthProvider(
                github_client_id,
                github_client_secret,
                github_redirect_uri
            )
    
    def get_provider(self, provider_name: str) -> Optional[OAuthProvider]:
        """Get OAuth provider by name"""
        return self.providers.get(provider_name)
    
    def get_available_providers(self) -> list:
        """Get list of available OAuth providers"""
        return list(self.providers.keys())
    
    async def get_authorization_url(self, provider_name: str, state: str) -> str:
        """Get authorization URL for specific provider"""
        provider = self.get_provider(provider_name)
        if not provider:
            raise ValueError(f"Provider '{provider_name}' not found or not configured")
        
        return await provider.get_authorization_url(state)
    
    async def get_user_info(self, provider_name: str, code: str) -> Dict[str, Any]:
        """Get user info from OAuth provider"""
        provider = self.get_provider(provider_name)
        if not provider:
            raise ValueError(f"Provider '{provider_name}' not found or not configured")
        
        return await provider.get_user_info(code)


# Global OAuth manager instance
oauth_manager = OAuthManager() 
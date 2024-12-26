import os
import sys
from telethon import TelegramClient
from telethon.tl.functions.messages import GetRepliesRequest
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
from dotenv import load_dotenv
import asyncio
import json
from tqdm import tqdm
import argparse

# Load environment variables
load_dotenv('config.env')

class ChannelAnalyzer:
    def __init__(self, session_name='anon'):
        self.api_id = os.getenv('API_ID')
        self.api_hash = os.getenv('API_HASH')
        self.session_name = session_name
        self.client = TelegramClient(session_name, self.api_id, self.api_hash)
        self.data = []
        self.channel_name = None
        
    async def connect(self):
        """Connect to Telegram"""
        await self.client.start()
        
    async def get_channel_messages(self, channel_username, limit=None):
        """Fetch all messages from a channel"""
        print(f"\n📱 Connecting to channel: {channel_username}")
        channel = await self.client.get_entity(channel_username)
        self.channel_name = channel.title
        messages = []
        
        # 获取消息总数以显示进度
        total = 0
        async for _ in self.client.iter_messages(channel, limit=1):
            total += 1
        
        print(f"📊 Found {total} messages in channel: {self.channel_name}")
        print("⏳ Fetching messages and comments...")
            
        with tqdm(total=total, desc="Progress", unit="msgs") as pbar:
            async for message in self.client.iter_messages(channel, limit=limit):
                if message.text:  # Only process messages with text
                    message_data = {
                        'id': message.id,
                        'date': message.date.isoformat(),
                        'text': message.text,
                        'views': getattr(message, 'views', 0),
                        'replies': getattr(message, 'replies', None),
                        'sender': getattr(message.sender, 'username', None) or getattr(message.sender, 'first_name', 'Unknown'),
                        'comments': []
                    }
                    
                    # Get comments if available
                    if message.replies:
                        try:
                            replies = await self.client.get_messages(
                                channel,
                                reply_to=message.id,
                                limit=100  # Limit comments per post
                            )
                            
                            for reply in replies:
                                if reply.text:
                                    comment_data = {
                                        'id': reply.id,
                                        'date': reply.date.isoformat(),
                                        'text': reply.text,
                                        'sender_username': getattr(reply.sender, 'username', None) or getattr(reply.sender, 'first_name', 'Unknown')
                                    }
                                    message_data['comments'].append(comment_data)
                        except Exception as e:
                            continue
                    
                    messages.append(message_data)
                pbar.update(1)
        
        self.data = messages
        
        # Print summary
        total_comments = sum(len(msg['comments']) for msg in messages)
        print(f"\n✅ Analysis complete!")
        print(f"📝 Total messages processed: {len(messages)}")
        print(f"💬 Total comments collected: {total_comments}")
        print(f"📊 Average comments per post: {total_comments/len(messages):.1f}")
        
        return messages

    def generate_report(self, output_file='report.html'):
        """Generate HTML report with visualizations"""
        if not self.data:
            return

        print("\n📄 Generating HTML report...")
        
        # Convert data to pandas DataFrame
        df = pd.DataFrame(self.data)
        
        def format_username(username):
            """Format username as a Telegram link"""
            if not username:
                return "Unknown"
            # Remove @ if present
            username = username.lstrip('@')
            return f'<a href="https://t.me/{username}" target="_blank">@{username}</a>'
        
        # Generate HTML content
        html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>Channel Analysis Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ background-color: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1200px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px solid #eee; }}
        .post {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .post-content {{ margin: 10px 0; }}
        .comments {{ margin-left: 20px; padding-left: 20px; border-left: 3px solid #dee2e6; }}
        .comment {{ background: white; padding: 10px; margin: 10px 0; border-radius: 5px; }}
        .username {{ color: #2980b9; font-weight: bold; }}
        .username a {{ color: #2980b9; text-decoration: none; }}
        .username a:hover {{ color: #3498db; text-decoration: underline; }}
        .date {{ color: #95a5a6; font-size: 0.9em; }}
        h1 {{ color: #2c3e50; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Channel Analysis Report</h1>
            <div class="channel-name">{format_username(self.channel_name)}</div>
            <div class="date">Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>

        <div class="posts">'''

        # Add each post and its comments
        for post in self.data:
            html_content += f'''
            <div class="post">
                <div class="post-header">
                    <span class="username">{format_username(post['sender'])}</span>
                    <span class="date">{datetime.fromisoformat(post['date']).strftime('%Y-%m-%d %H:%M')}</span>
                </div>
                <div class="post-content">{post['text']}</div>'''
            
            if post['comments']:
                html_content += f'''
                <div class="comments">
                    <h6>Comments ({len(post['comments'])})</h6>'''
                
                for comment in post['comments']:
                    html_content += f'''
                    <div class="comment">
                        <span class="username">{format_username(comment['sender_username'])}</span>
                        <span class="date">{datetime.fromisoformat(comment['date']).strftime('%Y-%m-%d %H:%M')}</span>
                        <div>{comment['text']}</div>
                    </div>'''
                
                html_content += '''
                </div>'''
            
            html_content += '''
            </div>'''

        html_content += '''
        </div>
    </div>
</body>
</html>'''
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✨ Report generated: {output_file}")

async def main():
    # 设置命令行参数解析
    parser = argparse.ArgumentParser(description='Analyze Telegram channel messages and comments')
    parser.add_argument('channel', help='Telegram channel username (e.g., @channel_name)')
    parser.add_argument('-p', '--posts', type=int, default=None, 
                      help='Number of posts to analyze (default: all posts)')
    
    args = parser.parse_args()
    
    # 验证频道用户名
    channel_username = args.channel
    if not channel_username.startswith('@'):
        channel_username = '@' + channel_username
    
    analyzer = ChannelAnalyzer()
    
    try:
        await analyzer.connect()
        await analyzer.get_channel_messages(channel_username, limit=args.posts)
        analyzer.generate_report()
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)
    finally:
        await analyzer.client.disconnect()
        print("\n📄 Generating HTML report...")
        print("✨ Report generated: report.html")

if __name__ == "__main__":
    asyncio.run(main())

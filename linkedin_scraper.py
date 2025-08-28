# LinkedIn Job Search Automation
# Daily automated search for Salesforce/Data contract opportunities in Europe

import asyncio
import random
import smtplib
import os
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from playwright.async_api import async_playwright
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LinkedInJobScraper:
    def __init__(self):
        self.email = os.getenv('LINKEDIN_EMAIL')
        self.password = os.getenv('LINKEDIN_PASSWORD')
        self.recipient_email = os.getenv('RECIPIENT_EMAIL')
        self.smtp_email = os.getenv('SMTP_EMAIL')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        
        # Multiple search query variations to rotate through
        self.search_queries = [
            # Primary recommended query
            """(salesforce OR "program manager" OR "release manager" OR "data strategy" OR "agile coach" OR CDP OR martech OR "business intelligence" OR CRM OR "digital transformation") AND (contract OR freelance OR consultant OR "looking for" OR "seeking" OR "need" OR "hiring" OR "project" OR "interim") AND (remote OR europe OR EU OR "work from home" OR WFH)""",
            
            # Role-specific focus
            """("salesforce architect" OR "program manager" OR "release manager" OR "CDP specialist" OR "agile coach" OR "BI manager" OR "data strategist") AND (freelance OR contract OR consultant OR "3-6 months" OR "6-12 months" OR interim OR project) AND (remote OR "remote work" OR europe)""",
            
            # Technology + opportunity focus
            """(salesforce OR tableau OR "marketing cloud" OR "service cloud" OR agile OR scrum OR "data analytics" OR CDP OR martech) AND ("looking for" OR "need a" OR "seeking" OR hiring OR contract OR freelance OR consultant) AND (remote OR EU OR europe OR "work from anywhere")""",
            
            # Industry-specific
            """(salesforce OR "program management" OR "release management" OR "agile transformation" OR "data strategy") AND (pharma OR retail OR healthcare OR telecom OR "life sciences" OR fintech OR banking) AND (contract OR freelance OR consultant OR "project basis") AND (remote OR europe)"""
        ]
        
        # Enhanced exclusion terms for job seekers
        self.exclusions = [
            "open to work", "opentowork", "looking for opportunities",
            "seeking new role", "job search", "career change", 
            "actively looking", "available for hire", "seeking opportunities",
            "#opentowork", "jobseekers", "candidates", "seeking a position"
        ]
        
        # Persona-specific keywords for quality scoring
        self.persona_keywords = {
            'martech_cdp': ['CDP', 'customer data platform', 'martech', 'marketing cloud', 'personalization'],
            'agile_coach': ['agile', 'scrum', 'transformation', 'coaching', 'scaled agile', 'SAFe'],
            'service_cloud': ['service cloud', 'case management', 'field service', 'customer service'],
            'program_manager': ['program manager', 'project manager', 'PMO', 'portfolio management'],
            'bi_analytics': ['tableau', 'business intelligence', 'analytics', 'einstein analytics', 'CRM analytics'],
            'solution_architect': ['architect', 'technical design', 'integration', 'API', 'system design'],
            'release_manager': ['release', 'deployment', 'devops', 'CI/CD', 'change management'],
            'data_strategy': ['data strategy', 'data governance', 'data architecture', 'MDM'],
            'transformation': ['digital transformation', 'change management', 'organizational change'],
            'industry_specific': ['pharma', 'healthcare', 'retail', 'telecom', 'financial services', 'life sciences']
        }
        
    async def random_delay(self, min_seconds=2, max_seconds=5):
        """Add human-like delays"""
        await asyncio.sleep(random.uniform(min_seconds, max_seconds))
        
    async def human_like_scroll(self, page):
        """Simulate human scrolling behavior"""
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, window.innerHeight * 0.7)")
            await self.random_delay(1, 3)
            
    async def login_to_linkedin(self, page):
        """Login to LinkedIn with human-like behavior"""
        try:
            logger.info("Navigating to LinkedIn login...")
            await page.goto('https://www.linkedin.com/login')
            await self.random_delay(3, 5)
            
            # Fill email
            await page.fill('input[name="session_key"]', self.email)
            await self.random_delay(1, 2)
            
            # Fill password
            await page.fill('input[name="session_password"]', self.password)
            await self.random_delay(1, 2)
            
            # Click login
            await page.click('button[type="submit"]')
            await page.wait_for_load_state('networkidle')
            await self.random_delay(3, 5)
            
            logger.info("Successfully logged in to LinkedIn")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
            
    async def search_posts(self, page):
        """Search for relevant job posts using rotating queries"""
        all_posts = []
        
        try:
            # Rotate through different search queries to catch more opportunities
            today = datetime.now()
            query_index = today.day % len(self.search_queries)  # Rotate daily
            current_query = self.search_queries[query_index]
            
            logger.info(f"Using query variation #{query_index + 1}: {current_query[:100]}...")
            
            # Navigate to search with NOT exclusions
            full_query = f"{current_query} NOT (\"open to work\" OR \"opentowork\" OR \"seeking opportunities\" OR \"#opentowork\")"
            search_url = f'https://www.linkedin.com/search/results/content/?keywords={full_query}&origin=GLOBAL_SEARCH_HEADER&sortBy="date_posted"'
            await page.goto(search_url)
            await page.wait_for_load_state('networkidle')
            await self.random_delay(3, 5)
            
            # Scroll to load more posts
            await self.human_like_scroll(page)
            
            # Extract posts
            posts = await page.evaluate("""
                () => {
                    const postElements = document.querySelectorAll('div[data-id]');
                    const posts = [];
                    
                    postElements.forEach((element, index) => {
                        if (index > 20) return; // Limit to first 20 posts
                        
                        try {
                            const textContent = element.textContent || '';
                            const timeElement = element.querySelector('span.update-components-actor__sub-description');
                            const authorElement = element.querySelector('.update-components-actor__name');
                            const linkElement = element.querySelector('a[href*="/posts/"]');
                            
                            posts.push({
                                text: textContent.substring(0, 500), // First 500 chars
                                author: authorElement ? authorElement.textContent.trim() : 'Unknown',
                                time: timeElement ? timeElement.textContent.trim() : 'Unknown',
                                url: linkElement ? 'https://www.linkedin.com' + linkElement.getAttribute('href').split('?')[0] : '',
                                id: element.getAttribute('data-id') || `post_${index}`
                            });
                        } catch (e) {
                            console.log('Error extracting post:', e);
                        }
                    });
                    
                    return posts.filter(post => post.url && post.text.length > 50);
                }
            """)
            
            logger.info(f"Found {len(posts)} posts using query variation #{query_index + 1}")
            return posts, current_query[:50] + "..."
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return [], "Search failed"
            
    def filter_quality_leads(self, posts):
        """Filter posts to find high-quality job opportunities using persona matching"""
        quality_leads = []
        
        for post in posts:
            text_lower = post['text'].lower()
            
            # Skip if contains job seeker language
            if any(exclusion in text_lower for exclusion in self.exclusions):
                continue
                
            # Enhanced hiring signals
            hiring_signals = [
                'hiring', 'looking for', 'seeking', 'need', 'opportunity',
                'position', 'role', 'join our team', 'we are looking',
                'contract position', 'freelance opportunity', 'consultant needed',
                'project starts', 'immediate start', 'urgently need'
            ]
            
            # Quality and urgency indicators
            quality_indicators = [
                'urgent', 'asap', 'start immediately', 'competitive rate',
                'remote first', 'flexible', 'experienced', 'senior',
                '3-6 months', '6-12 months', 'interim', 'transformation',
                'enterprise', 'global', 'multinational'
            ]
            
            # EU countries and remote work indicators
            location_indicators = [
                'germany', 'netherlands', 'france', 'spain', 'italy',
                'poland', 'sweden', 'denmark', 'austria', 'belgium',
                'ireland', 'portugal', 'finland', 'norway', 'switzerland',
                'europe', 'EU', 'european union', 'remote', 'work from home',
                'WFH', 'work from anywhere', 'timezone', 'CET', 'GMT'
            ]
            
            # Industry indicators (matching your experience)
            industry_signals = [
                'pharma', 'pharmaceutical', 'healthcare', 'life sciences',
                'retail', 'beauty', 'cosmetics', 'telecom', 'telco',
                'financial services', 'fintech', 'banking', 'insurance'
            ]
            
            # Scoring system with persona matching
            score = 0
            persona_matches = []
            
            # Base scoring
            if any(signal in text_lower for signal in hiring_signals):
                score += 4
            if any(indicator in text_lower for indicator in quality_indicators):
                score += 2
            if any(location in text_lower for location in location_indicators):
                score += 2
            if any(industry in text_lower for industry in industry_signals):
                score += 2
                
            # Persona-specific scoring
            for persona, keywords in self.persona_keywords.items():
                matches = sum(1 for keyword in keywords if keyword.lower() in text_lower)
                if matches > 0:
                    score += matches * 2
                    persona_matches.append(f"{persona}({matches})")
            
            # Boost score for contract/freelance specific mentions
            if any(term in text_lower for term in ['contract', 'freelance', 'consultant', 'interim']):
                score += 2
                
            # Boost for immediate availability needs
            if any(term in text_lower for term in ['urgent', 'asap', 'immediately', 'start soon']):
                score += 3
                
            if score >= 4:  # Minimum quality threshold
                post['quality_score'] = min(score, 10)  # Cap at 10
                post['persona_matches'] = persona_matches
                post['search_terms_found'] = [term for term in hiring_signals + quality_indicators if term in text_lower]
                quality_leads.append(post)
                
        # Sort by quality score and return top 9
        quality_leads.sort(key=lambda x: x['quality_score'], reverse=True)
        return quality_leads[:9]
        
    def create_email_content(self, leads, search_query_used):
        """Create enhanced HTML email with persona-matched job leads"""
        if not leads:
            return f"No quality job leads found today using search: '{search_query_used}'. The search will continue tomorrow with a different query variation!"
            
        html_content = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background-color: #0077B5; color: white; padding: 15px; border-radius: 5px; }
                .lead { border: 1px solid #ddd; margin: 15px 0; padding: 15px; border-radius: 5px; }
                .score { background-color: #f0f8f0; padding: 5px; border-radius: 3px; font-weight: bold; }
                .url { color: #0077B5; text-decoration: none; }
                .summary { background-color: #f9f9f9; padding: 10px; margin: 10px 0; }
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🎯 Daily LinkedIn Job Leads - """ + datetime.now().strftime('%B %d, %Y') + """</h2>
                <p>Found """ + str(len(leads)) + """ quality opportunities for you!</p>
                <p><small>🔍 Search Strategy: """ + search_query_used + """</small></p>
            </div>
        """
        
        for i, lead in enumerate(leads, 1):
            persona_info = ""
            if lead.get('persona_matches'):
                persona_info = f"<br><span style='color: #0077B5;'>👤 Persona Matches: {', '.join(lead['persona_matches'])}</span>"
                
            search_terms_info = ""
            if lead.get('search_terms_found'):
                search_terms_info = f"<br><span style='color: #28a745;'>🎯 Key Terms: {', '.join(lead['search_terms_found'][:3])}</span>"
            
            html_content += f"""
            <div class="lead">
                <h3>🚀 Lead #{i} - Quality Score: <span class="score">{lead['quality_score']}/10</span></h3>
                <p><strong>Author:</strong> {lead['author']}</p>
                <p><strong>Posted:</strong> {lead['time']}{persona_info}{search_terms_info}</p>
                <div class="summary">
                    <strong>Content Preview:</strong><br>
                    {lead['text'][:350]}{'...' if len(lead['text']) > 350 else ''}
                </div>
                <p><strong>🔗 LinkedIn Post:</strong> <a href="{lead['url']}" class="url" target="_blank">View & Engage with Post</a></p>
            </div>
            """
            
        html_content += """
            <div style="margin-top: 30px; padding: 15px; background-color: #f0f8ff; border-radius: 5px;">
                <h4>💡 Engagement Strategy (Based on Your Experience):</h4>
                <ul>
                    <li><strong>First</strong>: Like and comment on posts within 2-4 hours</li>
                    <li><strong>Then</strong>: Send personalized message referencing your 25+ country experience</li>
                    <li><strong>Highlight</strong>: GE Healthcare, L'Occitane, Deutsche Glasfaser experience for credibility</li>
                    <li><strong>Mention</strong>: EU timezone advantage and immediate availability</li>
                    <li><strong>Lead with value</strong>: Specific persona expertise (MarTech/CDP, Agile, Program Management)</li>
                </ul>
                <p><strong>🔄 Tomorrow's search will use a different query variation to catch more opportunities!</strong></p>
            </div>
        </body>
        </html>
        """
        return html_content
        
    async def send_email(self, leads, search_query_used):
        """Send email with job leads"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🎯 {len(leads)} LinkedIn Opportunities - {datetime.now().strftime('%B %d')} - Score {sum(lead['quality_score'] for lead in leads)}/90"
            msg['From'] = self.smtp_email
            msg['To'] = self.recipient_email
            
            html_content = self.create_email_content(leads, search_query_used)
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.smtp_email, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email sent successfully with {len(leads)} leads (total quality score: {sum(lead['quality_score'] for lead in leads)})")
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            
    async def run_daily_search(self):
        """Main function to run the daily search"""
        logger.info("Starting daily LinkedIn job search...")
        
        async with async_playwright() as p:
            # Launch browser with stealth settings
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-images'  # Faster loading
                ]
            )
            
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = await context.new_page()
            
            try:
                # Login to LinkedIn
                if await self.login_to_linkedin(page):
                    # Search for posts with rotating queries
                    all_posts, search_query_used = await self.search_posts(page)
                    
                    # Filter for quality leads with persona matching
                    quality_leads = self.filter_quality_leads(all_posts)
                    
                    # Send email with results
                    await self.send_email(quality_leads, search_query_used)
                    
                    logger.info(f"Daily search completed. Found {len(quality_leads)} quality leads using query: {search_query_used}")
                    
                else:
                    logger.error("Failed to login to LinkedIn")
                    
            except Exception as e:
                logger.error(f"Error during execution: {e}")
                
            finally:
                await browser.close()

# GitHub Actions entry point
async def main():
    scraper = LinkedInJobScraper()
    await scraper.run_daily_search()

if __name__ == "__main__":
    asyncio.run(main())

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
        
        # SIMPLIFIED search queries - LinkedIn struggles with complex OR queries
        # Using LinkedIn Jobs section instead of general posts
        self.search_queries = [
            "Salesforce contract remote",
            "Salesforce freelance Europe", 
            "CDP consultant remote",
            "Salesforce architect contract",
            "Agile coach freelance remote"
        ]
        
    async def random_delay(self, min_seconds=3, max_seconds=7):
        """Add human-like delays - increased for stealth"""
        await asyncio.sleep(random.uniform(min_seconds, max_seconds))
        
    async def human_like_scroll(self, page):
        """Simulate human scrolling behavior"""
        for _ in range(random.randint(2, 4)):
            scroll_amount = random.randint(300, 700)
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await self.random_delay(2, 4)
            
    async def login_to_linkedin(self, page):
        """Login to LinkedIn with enhanced stealth"""
        try:
            logger.info("Navigating to LinkedIn login...")
            await page.goto('https://www.linkedin.com/login', wait_until='networkidle')
            await self.random_delay(4, 6)
            
            # Human-like typing
            email_field = await page.query_selector('input[name="session_key"]')
            for char in self.email:
                await email_field.type(char, delay=random.randint(50, 150))
            await self.random_delay(1, 2)
            
            # Fill password
            password_field = await page.query_selector('input[name="session_password"]')
            for char in self.password:
                await password_field.type(char, delay=random.randint(50, 150))
            await self.random_delay(1, 3)
            
            # Click login
            await page.click('button[type="submit"]')
            await page.wait_for_load_state('networkidle', timeout=30000)
            await self.random_delay(5, 8)
            
            # Check if login successful
            current_url = page.url
            if 'feed' in current_url or 'checkpoint' not in current_url:
                logger.info("Successfully logged in to LinkedIn")
                return True
            else:
                logger.error(f"Login verification failed. Current URL: {current_url}")
                return False
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    async def search_jobs_section(self, page):
        """Search LinkedIn JOBS section (not posts) - more reliable"""
        all_jobs = []
        
        try:
            # Use the week to determine which query to use
            week_of_year = datetime.now().isocalendar()[1]
            query_index = week_of_year % len(self.search_queries)
            current_query = self.search_queries[query_index]
            
            logger.info(f"Using query: {current_query}")
            
            # Navigate to LinkedIn Jobs with simple search
            # Note: f_WT=2 means "Remote" jobs
            search_url = f'https://www.linkedin.com/jobs/search/?keywords={current_query}&f_WT=2&f_TPR=r604800&sortBy=DD'
            # f_TPR=r604800 means "Past Week"
            # sortBy=DD means "Most Recent"
            
            await page.goto(search_url, wait_until='networkidle', timeout=30000)
            await self.random_delay(5, 8)
            
            # Scroll to load more jobs
            await self.human_like_scroll(page)
            await self.random_delay(3, 5)
            
            # Extract job listings with enhanced selectors
            jobs = await page.evaluate("""
                () => {
                    const jobCards = document.querySelectorAll('div.job-card-container, li.jobs-search-results__list-item, div.jobs-search-results__list-item');
                    const jobs = [];
                    
                    jobCards.forEach((card, index) => {
                        if (index > 24) return; // Limit to 25 jobs
                        
                        try {
                            // Multiple selector strategies
                            const titleElement = card.querySelector('a.job-card-list__title, h3.job-card-list__title, a[data-tracking-control-name*="job"]');
                            const companyElement = card.querySelector('a.job-card-container__company-name, h4.job-card-container__company-name, span.job-card-container__company-name');
                            const locationElement = card.querySelector('li.job-card-container__metadata-item, span.job-card-container__metadata-item');
                            const linkElement = card.querySelector('a[href*="/jobs/view/"]');
                            const timeElement = card.querySelector('time, span[class*="time"]');
                            
                            const title = titleElement ? titleElement.textContent.trim() : '';
                            const company = companyElement ? companyElement.textContent.trim() : '';
                            const location = locationElement ? locationElement.textContent.trim() : '';
                            const url = linkElement ? linkElement.href : '';
                            const posted = timeElement ? timeElement.textContent.trim() : '';
                            
                            if (title && url) {
                                jobs.push({
                                    title: title,
                                    company: company,
                                    location: location,
                                    url: url,
                                    posted: posted,
                                    text: title + ' ' + company + ' ' + location // For filtering
                                });
                            }
                        } catch (e) {
                            console.log('Error extracting job:', e);
                        }
                    });
                    
                    return jobs;
                }
            """)
            
            logger.info(f"Found {len(jobs)} jobs using query: {current_query}")
            
            # If no jobs found, try screenshot for debugging
            if len(jobs) == 0:
                await page.screenshot(path='debug_screenshot.png')
                logger.warning("No jobs found - saved screenshot for debugging")
            
            return jobs, current_query
            
        except Exception as e:
            logger.error(f"Job search failed: {e}")
            # Save screenshot on error
            try:
                await page.screenshot(path='error_screenshot.png')
            except:
                pass
            return [], "Search failed"
    
    def filter_quality_jobs(self, jobs):
        """Filter jobs for quality and relevance"""
        quality_jobs = []
        
        for job in jobs:
            text_lower = (job['title'] + ' ' + job['company'] + ' ' + job['location']).lower()
            
            # Your core skills
            skill_matches = sum([
                2 if 'salesforce' in text_lower else 0,
                2 if 'architect' in text_lower else 0,
                1 if 'cdp' in text_lower or 'customer data' in text_lower else 0,
                1 if 'agile' in text_lower or 'scrum' in text_lower else 0,
                1 if 'program manager' in text_lower or 'project manager' in text_lower else 0,
                1 if 'tableau' in text_lower or 'analytics' in text_lower else 0,
                1 if 'marketing cloud' in text_lower or 'service cloud' in text_lower else 0
            ])
            
            # Contract/remote indicators
            contract_score = sum([
                2 if 'contract' in text_lower else 0,
                2 if 'freelance' in text_lower else 0,
                1 if 'consultant' in text_lower else 0,
                1 if 'remote' in text_lower else 0,
                1 if 'europe' in text_lower or 'eu' in text_lower else 0
            ])
            
            # Seniority match
            seniority_score = sum([
                2 if 'senior' in text_lower else 0,
                2 if 'lead' in text_lower else 0,
                1 if 'principal' in text_lower else 0,
                -2 if 'junior' in text_lower else 0  # Penalize junior roles
            ])
            
            total_score = skill_matches + contract_score + seniority_score
            
            if total_score >= 3:  # Minimum threshold
                job['quality_score'] = min(total_score, 10)
                quality_jobs.append(job)
        
        # Sort by score and return top 10
        quality_jobs.sort(key=lambda x: x['quality_score'], reverse=True)
        return quality_jobs[:10]
    
    def create_email_content(self, jobs, search_query_used):
        """Create HTML email with job listings"""
        if not jobs:
            return f"""
            <html>
            <body>
                <h2>⚠️ No Quality Jobs Found This Week</h2>
                <p>Search query used: <strong>{search_query_used}</strong></p>
                <p>Possible reasons:</p>
                <ul>
                    <li>LinkedIn may be blocking automated searches</li>
                    <li>No new matching jobs posted this week</li>
                    <li>Search criteria may need adjustment</li>
                </ul>
                <p><strong>Recommendation:</strong> Manually search LinkedIn Jobs this week</p>
            </body>
            </html>
            """
            
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .header {{ background-color: #0077B5; color: white; padding: 20px; border-radius: 8px; }}
                .job {{ border: 2px solid #ddd; margin: 15px 0; padding: 20px; background-color: white; border-radius: 8px; }}
                .job:hover {{ border-color: #0077B5; }}
                .score {{ background-color: #28a745; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold; }}
                .link {{ display: inline-block; background-color: #0077B5; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-top: 10px; }}
                .link:hover {{ background-color: #005885; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>💼 Weekly LinkedIn Job Leads - {datetime.now().strftime('%B %d, %Y')}</h2>
                <p>Found {len(jobs)} quality opportunities!</p>
                <p><small>🔍 Search: "{search_query_used}"</small></p>
            </div>
        """
        
        for i, job in enumerate(jobs, 1):
            html_content += f"""
            <div class="job">
                <h3>🎯 Job #{i} - Quality Score: <span class="score">{job['quality_score']}/10</span></h3>
                <p><strong>Title:</strong> {job['title']}</p>
                <p><strong>Company:</strong> {job['company']}</p>
                <p><strong>Location:</strong> {job['location']}</p>
                <p><strong>Posted:</strong> {job['posted']}</p>
                <a href="{job['url']}" class="link" target="_blank">View Job on LinkedIn →</a>
            </div>
            """
            
        html_content += """
            <div style="margin-top: 30px; padding: 20px; background-color: #fff3cd; border-radius: 8px;">
                <h4>💡 Next Steps:</h4>
                <ol>
                    <li>Apply to top 3 jobs within 24 hours</li>
                    <li>Customize your pitch for each role</li>
                    <li>Follow up after 3-4 days if no response</li>
                    <li>Network with employees at target companies</li>
                </ol>
            </div>
        </body>
        </html>
        """
        return html_content
    
    async def send_email(self, jobs, search_query_used):
        """Send email with job leads"""
        try:
            msg = MIMEMultipart('alternative')
            total_score = sum(job.get('quality_score', 0) for job in jobs)
            msg['Subject'] = f"💼 {len(jobs)} Salesforce Jobs This Week - Score: {total_score}/100"
            msg['From'] = self.smtp_email
            msg['To'] = self.recipient_email
            
            html_content = self.create_email_content(jobs, search_query_used)
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.smtp_email, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email sent successfully with {len(jobs)} jobs")
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
    
    async def run_weekly_search(self):
        """Main function to run the weekly search"""
        logger.info("Starting weekly LinkedIn job search...")
        
        async with async_playwright() as p:
            # Enhanced browser launch with stealth
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-extensions',
                    '--disable-gpu',
                    '--window-size=1920,1080'
                ]
            )
            
            # More realistic context
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='en-US',
                timezone_id='Europe/Warsaw'
            )
            
            page = await context.new_page()
            
            try:
                # Login to LinkedIn
                if await self.login_to_linkedin(page):
                    # Search LinkedIn Jobs section
                    all_jobs, search_query_used = await self.search_jobs_section(page)
                    
                    # Filter for quality
                    quality_jobs = self.filter_quality_jobs(all_jobs)
                    
                    # Send email
                    await self.send_email(quality_jobs, search_query_used)
                    
                    logger.info(f"Weekly search completed. Found {len(quality_jobs)} quality jobs")
                else:
                    logger.error("Failed to login to LinkedIn")
                    # Send alert email about login failure
                    await self.send_email([], "Login Failed")
                    
            except Exception as e:
                logger.error(f"Error during execution: {e}")
                await self.send_email([], f"Error: {str(e)}")
                
            finally:
                await browser.close()

async def main():
    scraper = LinkedInJobScraper()
    await scraper.run_weekly_search()

if __name__ == "__main__":
    asyncio.run(main())

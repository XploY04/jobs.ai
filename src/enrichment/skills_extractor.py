"""Rule-based skills and tech stack extraction"""

import re
from typing import List, Set


class SkillsExtractor:
    """Extract technical skills from job descriptions using pattern matching"""

    # Comprehensive tech stack patterns
    TECH_PATTERNS = {
        # Programming Languages
        'python': r'\b(?:python|django|flask|fastapi|pandas|numpy)\b',
        'javascript': r'\b(?:javascript|js|typescript|ts|node\.?js|deno)\b',
        'java': r'\b(?:java|spring|springboot|hibernate)\b',
        'golang': r'\b(?:go|golang)\b',
        'rust': r'\b(?:rust|cargo)\b',
        'ruby': r'\b(?:ruby|rails|ruby on rails)\b',
        'php': r'\b(?:php|laravel|symfony|wordpress)\b',
        'c++': r'\b(?:c\+\+|cpp)\b',
        'c#': r'\b(?:c#|csharp|\.net|dotnet)\b',
        'swift': r'\b(?:swift|swiftui)\b',
        'kotlin': r'\b(?:kotlin)\b',
        'scala': r'\b(?:scala|akka)\b',
        
        # Frontend Frameworks
        'react': r'\b(?:react|reactjs|react\.js|nextjs|next\.js)\b',
        'vue': r'\b(?:vue|vuejs|vue\.js|nuxt)\b',
        'angular': r'\b(?:angular|angularjs)\b',
        'svelte': r'\b(?:svelte|sveltekit)\b',
        
        # Backend Frameworks
        'express': r'\b(?:express|expressjs|express\.js)\b',
        'nestjs': r'\b(?:nestjs|nest\.js)\b',
        
        # Databases
        'postgresql': r'\b(?:postgres|postgresql|psql)\b',
        'mysql': r'\b(?:mysql|mariadb)\b',
        'mongodb': r'\b(?:mongodb|mongo)\b',
        'redis': r'\b(?:redis|valkey)\b',
        'elasticsearch': r'\b(?:elasticsearch|elastic|elk)\b',
        'cassandra': r'\b(?:cassandra)\b',
        'dynamodb': r'\b(?:dynamodb)\b',
        
        # Cloud Platforms
        'aws': r'\b(?:aws|amazon web services|ec2|s3|lambda|rds|ecs|eks)\b',
        'gcp': r'\b(?:gcp|google cloud|gke|bigquery)\b',
        'azure': r'\b(?:azure|microsoft azure)\b',
        'digitalocean': r'\b(?:digitalocean|do)\b',
        
        # DevOps & Tools
        'docker': r'\b(?:docker|dockerfile|containers?)\b',
        'kubernetes': r'\b(?:kubernetes|k8s|kubectl|helm)\b',
        'terraform': r'\b(?:terraform|tf)\b',
        'ansible': r'\b(?:ansible)\b',
        'jenkins': r'\b(?:jenkins)\b',
        'github actions': r'\b(?:github actions|gh actions)\b',
        'gitlab ci': r'\b(?:gitlab ci|gitlab)\b',
        'circleci': r'\b(?:circleci|circle ci)\b',
        
        # Monitoring & Observability
        'prometheus': r'\b(?:prometheus)\b',
        'grafana': r'\b(?:grafana)\b',
        'datadog': r'\b(?:datadog)\b',
        'newrelic': r'\b(?:new relic|newrelic)\b',
        
        # Message Queues
        'kafka': r'\b(?:kafka|apache kafka)\b',
        'rabbitmq': r'\b(?:rabbitmq|rabbit mq)\b',
        'sqs': r'\b(?:sqs|amazon sqs)\b',
        
        # Testing
        'pytest': r'\b(?:pytest)\b',
        'jest': r'\b(?:jest)\b',
        'cypress': r'\b(?:cypress)\b',
        'selenium': r'\b(?:selenium)\b',
        
        # Version Control
        'git': r'\b(?:git|github|gitlab|bitbucket)\b',
        
        # CI/CD
        'ci/cd': r'\b(?:ci/cd|cicd|continuous integration|continuous deployment)\b',
        
        # Methodologies
        'agile': r'\b(?:agile|scrum|kanban)\b',
        'microservices': r'\b(?:microservices?|micro-services?)\b',
        'rest api': r'\b(?:rest|restful|rest api)\b',
        'graphql': r'\b(?:graphql|gql)\b',
    }

    def extract(self, title: str, description: str) -> List[str]:
        """Extract skills from job title and description"""
        
        # Combine and lowercase for matching
        text = f"{title} {description}".lower()
        
        # Find all matching skills
        found_skills: Set[str] = set()
        
        for skill_name, pattern in self.TECH_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                found_skills.add(skill_name)
        
        return sorted(list(found_skills))

    def categorize_role(self, title: str, description: str, skills: List[str]) -> str:
        """Categorize the role based on skills and job details"""
        
        text = f"{title} {description}".lower()
        title_lower = title.lower()
        
        # First, check if this is a non-technical role (sales, marketing, HR, etc.)
        # These should NOT be categorized as backend/frontend/devops even if tech is mentioned
        non_technical_keywords = [
            'sales', 'account executive', 'account manager', 'business development',
            'marketing', 'recruiter', 'recruiting', 'hr ', 'human resources',
            'operations', 'finance', 'legal', 'compliance', 'customer success',
            'support', 'content', 'copywriter', 
            'product manager', 'product owner', 'project manager', 'program manager',
            'analyst', 'business analyst', 'data analyst'  # Note: data analyst is different from data engineer
        ]
        
        # Check title first (most important signal) - but exclude engineering managers
        # Engineering Manager is technical, but Sales Manager is not
        is_engineering_manager = 'engineering manager' in title_lower or 'eng manager' in title_lower
        
        if not is_engineering_manager:
            for keyword in non_technical_keywords:
                if keyword in title_lower:
                    return 'general'
        
        # Special handling for design roles
        if any(keyword in title_lower for keyword in ['designer', 'ux', 'ui', 'design lead']):
            # Only UX/UI designers without "engineer" should be general
            if 'engineer' not in title_lower and 'developer' not in title_lower:
                return 'general'
        
        # Frontend indicators
        frontend_score = sum([
            'react' in skills or 'vue' in skills or 'angular' in skills,
            'frontend' in text or 'front-end' in text,
            'ui' in text or 'ux' in text,
            'css' in text or 'html' in text
        ])
        
        # Backend indicators
        backend_score = sum([
            'backend' in text or 'back-end' in text,
            'api' in text,
            any(db in skills for db in ['postgresql', 'mysql', 'mongodb']),
            any(lang in skills for lang in ['python', 'java', 'golang', 'ruby'])
        ])
        
        # DevOps indicators
        devops_score = sum([
            'devops' in text or 'sre' in text,
            'docker' in skills or 'kubernetes' in skills,
            'terraform' in skills or 'ansible' in skills,
            'ci/cd' in skills,
            any(cloud in skills for cloud in ['aws', 'gcp', 'azure'])
        ])
        
        # Data indicators
        data_score = sum([
            'data engineer' in text or 'data scientist' in text,
            'spark' in text or 'airflow' in text,
            'etl' in text or 'pipeline' in text,
            'bigquery' in text or 'redshift' in text
        ])
        
        # ML/AI indicators
        ml_score = sum([
            'machine learning' in text or 'ml' in text,
            'ai' in text or 'artificial intelligence' in text,
            'pytorch' in text or 'tensorflow' in text,
            'nlp' in text or 'computer vision' in text
        ])
        
        # Determine primary category
        scores = {
            'frontend': frontend_score,
            'backend': backend_score,
            'devops': devops_score,
            'data': data_score,
            'ml': ml_score
        }
        
        max_score = max(scores.values())
        
        if max_score == 0:
            return 'general'
        
        # Full stack if both frontend and backend are high
        if backend_score >= 2 and frontend_score >= 2:
            return 'fullstack'
        
        return max(scores, key=scores.get)

/**
 * HeyZack Brochure Interactive Features
 */

(function() {
    'use strict';
    
    // Initialize when DOM is loaded
    document.addEventListener('DOMContentLoaded', function() {
        initSmoothScrolling();
        initImageLazyLoading();
        initPrintOptimization();
        addAccessibilityFeatures();
    });
    
    /**
     * Smooth scrolling for category navigation
     */
    function initSmoothScrolling() {
        const categoryLinks = document.querySelectorAll('.category-card a[href^="#"]');
        
        categoryLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                
                const targetId = this.getAttribute('href').substring(1);
                const targetElement = document.getElementById(targetId);
                
                if (targetElement) {
                    targetElement.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                    
                    // Add visual feedback
                    targetElement.style.transition = 'background-color 0.3s ease';
                    targetElement.style.backgroundColor = 'rgba(212, 175, 55, 0.1)';
                    
                    setTimeout(() => {
                        targetElement.style.backgroundColor = '';
                    }, 1000);
                }
            });
        });
    }
    
    /**
     * Enhanced image lazy loading with error handling
     */
    function initImageLazyLoading() {
        const images = document.querySelectorAll('.product-image img[loading="lazy"]');
        
        // Add error handling for broken images
        images.forEach(img => {
            img.addEventListener('error', function() {
                const placeholder = document.createElement('div');
                placeholder.className = 'image-placeholder';
                placeholder.innerHTML = `<span>${this.alt.substring(0, 2).toUpperCase()}</span>`;
                
                this.parentNode.replaceChild(placeholder, this);
            });
            
            img.addEventListener('load', function() {
                this.style.opacity = '0';
                this.style.transition = 'opacity 0.3s ease';
                setTimeout(() => {
                    this.style.opacity = '1';
                }, 50);
            });
        });
    }
    
    // Search functionality removed for modern brochure design
    
    /**
     * Print optimization
     */
    function initPrintOptimization() {
        window.addEventListener('beforeprint', function() {
            // Expand all truncated content for printing
            document.querySelectorAll('.product-description').forEach(desc => {
                desc.style.webkitLineClamp = 'unset';
                desc.style.overflow = 'visible';
            });
        });
        
        window.addEventListener('afterprint', function() {
            // Restore truncated content after printing
            document.querySelectorAll('.product-description').forEach(desc => {
                desc.style.webkitLineClamp = '';
                desc.style.overflow = '';
            });
        });
    }
    
    /**
     * Add accessibility features
     */
    function addAccessibilityFeatures() {
        // Add keyboard navigation for product cards
        const productCards = document.querySelectorAll('.product-card');
        
        productCards.forEach((card, index) => {
            card.setAttribute('tabindex', '0');
            card.setAttribute('role', 'article');
            card.setAttribute('aria-label', `Product ${index + 1}: ${card.querySelector('.product-name').textContent}`);
            
            card.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    // Focus on the first interactive element or scroll to it
                    this.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            });
        });
        
        // Add skip to content link
        const skipLink = document.createElement('a');
        skipLink.href = '#main-content';
        skipLink.textContent = 'Skip to main content';
        skipLink.className = 'skip-link';
        
        const skipLinkStyles = `
            .skip-link {
                position: absolute;
                top: -40px;
                left: 6px;
                background: var(--accent-color);
                color: var(--primary-color);
                padding: 8px;
                text-decoration: none;
                border-radius: 4px;
                z-index: 1000;
                transition: top 0.3s ease;
            }
            .skip-link:focus {
                top: 6px;
            }
        `;
        
        const styleSheet = document.createElement('style');
        styleSheet.textContent = skipLinkStyles;
        document.head.appendChild(styleSheet);
        
        document.body.insertBefore(skipLink, document.body.firstChild);
        
        // Add main content landmark
        const mainContent = document.querySelector('.product-catalog');
        if (mainContent) {
            mainContent.id = 'main-content';
            mainContent.setAttribute('role', 'main');
        }
    }
    
})();
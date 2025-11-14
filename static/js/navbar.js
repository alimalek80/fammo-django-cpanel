document.addEventListener('DOMContentLoaded', function () {
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');
    const mainNavbar = document.getElementById('main-navbar');
    let lastScrollTop = 0;

    // Toggle mobile menu on hamburger click
    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            mobileMenu.classList.toggle('hidden');
            console.log('Mobile menu toggled, hidden class:', mobileMenu.classList.contains('hidden'));
        });

        // Close mobile menu when clicking outside
        document.addEventListener('click', function(e) {
            if (!mobileMenu.contains(e.target) && !mobileMenuButton.contains(e.target)) {
                if (!mobileMenu.classList.contains('hidden')) {
                    mobileMenu.classList.add('hidden');
                }
            }
        });
    } else {
        console.error('Mobile menu elements not found:', {
            button: !!mobileMenuButton,
            menu: !!mobileMenu
        });
    }

    // Hide/Show Navbar on Scroll
    if (mainNavbar) {
        window.addEventListener('scroll', function () {
            const currentScrollTop = window.pageYOffset || document.documentElement.scrollTop;

            if (currentScrollTop > lastScrollTop && currentScrollTop > 70) {
                mainNavbar.classList.add('navbar-hidden');
            } else if (currentScrollTop < lastScrollTop || currentScrollTop <= 70) {
                mainNavbar.classList.remove('navbar-hidden');
            }

            lastScrollTop = Math.max(0, currentScrollTop);
        });
    }

    // Pet type option selection
    const petTypeOptions = document.querySelectorAll('.pet-type-option input[type="radio"]');
    if (petTypeOptions.length > 0) {
        petTypeOptions.forEach(radio => {
            radio.addEventListener('change', function () {
                document.querySelectorAll('.pet-type-option').forEach(label => {
                    label.classList.remove('border-indigo-600', 'shadow-md', 'bg-indigo-50');
                });
                this.closest('label').classList.add('border-indigo-600', 'shadow-md', 'bg-indigo-50');
            });
        });
    }
});

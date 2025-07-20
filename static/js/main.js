// StyleHub - Main JavaScript File

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    })

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl)
    })

    // Price range slider for product filtering
    const priceRangeSlider = document.getElementById('price-range');
    if (priceRangeSlider) {
        const priceMin = document.getElementById('price-min');
        const priceMax = document.getElementById('price-max');
        
        noUiSlider.create(priceRangeSlider, {
            start: [0, 1000],
            connect: true,
            step: 10,
            range: {
                'min': 0,
                'max': 1000
            },
            format: {
                to: function (value) {
                    return Math.round(value);
                },
                from: function (value) {
                    return Number(value);
                }
            }
        });

        priceRangeSlider.noUiSlider.on('update', function (values, handle) {
            if (handle === 0) {
                priceMin.value = values[handle];
            } else {
                priceMax.value = values[handle];
            }
        });
    }

    // Product image gallery
    const productMainImage = document.getElementById('product-main-image');
    const productThumbnails = document.querySelectorAll('.product-thumbnail');
    
    if (productMainImage && productThumbnails.length > 0) {
        productThumbnails.forEach(thumbnail => {
            thumbnail.addEventListener('click', function() {
                const newSrc = this.getAttribute('data-src');
                productMainImage.src = newSrc;
                
                // Remove active class from all thumbnails
                productThumbnails.forEach(thumb => thumb.classList.remove('active'));
                
                // Add active class to clicked thumbnail
                this.classList.add('active');
            });
        });
    }

    // Quantity selector for product detail page
    const quantityInput = document.getElementById('quantity');
    const quantityPlus = document.getElementById('quantity-plus');
    const quantityMinus = document.getElementById('quantity-minus');
    
    if (quantityInput && quantityPlus && quantityMinus) {
        quantityPlus.addEventListener('click', function() {
            quantityInput.value = parseInt(quantityInput.value) + 1;
        });
        
        quantityMinus.addEventListener('click', function() {
            if (parseInt(quantityInput.value) > 1) {
                quantityInput.value = parseInt(quantityInput.value) - 1;
            }
        });
    }

    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });

    // Auto-hide flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.alert');
    
    flashMessages.forEach(message => {
        setTimeout(function() {
            message.classList.add('fade');
            setTimeout(function() {
                message.remove();
            }, 500);
        }, 5000);
    });

    // Toggle password visibility
    const togglePasswordButtons = document.querySelectorAll('.toggle-password');
    
    togglePasswordButtons.forEach(button => {
        button.addEventListener('click', function() {
            const passwordInput = document.querySelector(this.getAttribute('data-target'));
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);
            
            // Toggle icon
            this.querySelector('i').classList.toggle('fa-eye');
            this.querySelector('i').classList.toggle('fa-eye-slash');
        });
    });

    // Confirm delete modals
    const deleteButtons = document.querySelectorAll('[data-delete-target]');
    
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const target = this.getAttribute('data-delete-target');
            const confirmModal = new bootstrap.Modal(document.getElementById('confirm-delete-modal'));
            
            document.getElementById('confirm-delete-button').setAttribute('data-target', target);
            confirmModal.show();
        });
    });
    
    const confirmDeleteButton = document.getElementById('confirm-delete-button');
    
    if (confirmDeleteButton) {
        confirmDeleteButton.addEventListener('click', function() {
            const target = this.getAttribute('data-target');
            window.location.href = target;
        });
    }
});
document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector("form");
    form.addEventListener("submit", function () {
        console.log("Form submitted");
    });

    // Example: show password requirements on focus
    const passwordField = document.querySelector("input[name='password1']");
    if (passwordField) {
        passwordField.addEventListener("focus", () => {
            console.log("Password field focused");
        });
    }
});

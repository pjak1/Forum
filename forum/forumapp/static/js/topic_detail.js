let isReplying = false; // Flag to track submission state

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Check if this cookie string begins with the provided name
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function createReply(text, author, time) {
    const reply = document.createElement("li");
    const reply_text = document.createElement("p");
    const reply_info = document.createElement("p");

    reply.classList.add("list-group-item");
    reply_text.textContent = text;
    reply_info.classList.add("text-muted");
    reply_info.textContent = gettext(`Posted by ${author} on ${time}`);

    reply.appendChild(reply_text);
    reply.appendChild(reply_info);

    return reply;
}

function handleReply(textarea, responseSection, wrapper) {
    const content = textarea.value;
    const slug = responseSection.getAttribute("data");

    if (content.trim() && !isReplying) { // Check if submission is not in progress
        isReplying = true; // Set the flag to true

        // Prepare the data to send
        const data = { reply: content, topic_slug: slug };

        // Send the data to the new-reply URL
        fetch('/new-reply/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'), // Include CSRF token
            },
            body: JSON.stringify(data), // Convert the data to JSON
        })
        .then(response => {
            // Check if the response is OK (status code 200-299)
            if (!response.ok) {
                alert('Error submitting reply.');
                return Promise.reject('Error submitting reply.'); // Reject the promise to skip the next .then
            }
        
            // If response is ok, remove the wrapper and return the JSON data
            wrapper.remove();
            return response.json();
        })
        .then(data => {
            const replies = document.getElementById("replies");
            const username = document.getElementById("userDropdown").textContent;
        
            // Create the reply element using the response data
            const reply = createReply(content, username, data.time);
            const no_replies = document.getElementById("no_replies");

            if (no_replies) {
                no_replies.remove();
            }

            replies.appendChild(reply);
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error submitting reply: ' + error);
        })
        .finally(() => {
            isReplying = false; // Reset the flag after completion
        }); 
    }
}

function createReplyBox() {
    // Find the element where we want to insert the toolbar and textarea
    const responseSection = document.getElementById('reply_div');

    // Create a wrapper div with a border
    const wrapper = document.createElement('div');
    wrapper.id = "reply_wrapper";
    wrapper.classList.add('border', 'rounded', 'pb-3', 'mb-3'); // Add border and padding

    // Create a textarea element without a border
    const textarea = document.createElement('textarea');
    textarea.classList.add('form-control', 'border-0'); // Border-0 to remove the border
    textarea.setAttribute('rows', '5');
    textarea.setAttribute('placeholder', gettext('Write your reply here...'));
    textarea.style.resize = 'none';

    // Create a div for the toolbar
    const toolbar = document.createElement('div');
    toolbar.classList.add('d-flex', 'justify-content-end', 'mt-2');

    // Create the Reply button
    const replyButton = document.createElement('button');
    replyButton.classList.add('btn', 'btn-primary', 'me-2');
    replyButton.textContent = 'Reply';

    // Create the Cancel button
    const cancelButton = document.createElement('button');
    cancelButton.classList.add('btn', 'btn-secondary', 'me-2');
    cancelButton.textContent = 'Cancel';

    // Add the buttons to the toolbar
    toolbar.appendChild(replyButton);
    toolbar.appendChild(cancelButton);

    // Add the textarea and toolbar to the wrapper
    wrapper.appendChild(textarea);
    wrapper.appendChild(toolbar);

    // Add the wrapper to the response section
    responseSection.appendChild(wrapper);

    // Function for the action on the Cancel button
    cancelButton.addEventListener('click', function() {
        // Remove the textarea and toolbar from the DOM
        wrapper.remove();
    });

    // Function for the action on the Reply button
    replyButton.addEventListener('click', function() {
       handleReply(textarea, responseSection, wrapper);
    });
    // Add event listeners to apply active styles to the wrapper
    textarea.addEventListener('focus', function() {
        wrapper.classList.add('active-border'); // Add active class for the border
    });

    textarea.addEventListener('blur', function() {
        wrapper.classList.remove('active-border'); // Remove the active class when not focused
    });
}


var reply_button = document.getElementById("reply_button");

reply_button.addEventListener("click", () => {
    if (!document.getElementById("reply_wrapper")){
        createReplyBox();
    }
});

var isReplying = false; // Flag to track submission state
var page = 1;  // current page
var per_page = 7;
var model = "Reply";
const responseSection = document.getElementById('reply_div');
const slug = responseSection.getAttribute("data");

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

function handleReply(textarea, wrapper) {
    const content = textarea.value;

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
       handleReply(textarea, wrapper);
    });
    // Add event listeners to apply active styles to the wrapper
    textarea.addEventListener('focus', function() {
        wrapper.classList.add('active-border'); // Add active class for the border
    });

    textarea.addEventListener('blur', function() {
        wrapper.classList.remove('active-border'); // Remove the active class when not focused
    });
}

function loadReplies() {
    filters = {"topic__slug": slug};
    let body = `page=${page}&per_page=${per_page}&model=${model}`;
    
    for (const [key, value] of Object.entries(filters)) {
        body += `&${key}=${value}`;
    }

    loadObjects('/load-objects/?format_function=datetime_format&format_args[]=created_at&annotate_author_name=author__username',
    body,
    document.getElementById('replies'),
    filters,
    (object) => {
        return createReply(object.content, object.author_name, object.created_at);
    });
}

function handleScroll() {
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 100 && !isLoading) {
       loadReplies();
    }
}

var reply_button = document.getElementById("reply_button");

if (reply_button) {
    reply_button.addEventListener("click", () => {
        if (!document.getElementById("reply_wrapper")){
            createReplyBox();
        }
    });
    
}

// Load objects dynmically when scrolling down
window.addEventListener('scroll', handleScroll);

// Load dynamically first page of objects
document.addEventListener('DOMContentLoaded', loadReplies);

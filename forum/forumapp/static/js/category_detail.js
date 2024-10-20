let page = 1;
let per_page = 10;
let model = 'Topic';

function loadTopics() {
    let params = new URLSearchParams({
        page: page,
        per_page: per_page,
        model: model,
        related_counts: 'replies',
        format_function: 'datetime_format',
        'format_args[]': 'created_at',
        annotate_author_name: 'author__username'
    });
    let filters = {};
    let categorySlug =  document.getElementById('topics_div').getAttribute('data');

    if (categorySlug == 'MyTopics') {
        let userId = document.getElementById('new_topic_btn').getAttribute('data');
        filters['author_id'] = userId;
    } else {
        filters['category__slug'] = categorySlug;
    }

    let body = `page=${page}&per_page=${per_page}&model=${model}`;

    for (const [key, value] of Object.entries(filters)) {
        body += `&${key}=${value}`;
    }

    let categories = document.getElementById('topics');

    loadObjects(
        `/load-objects/?${params.toString()}`,
        body,
        categories,
        filters,
        (object) => {
            return createTopic(object.title, object.author_name, object.created_at, object.replies_count || 0, object.slug);
        }
    );
}

function createTopic(title, author, date, replies, slug) {
    // Create the list item element
    const listItem = document.createElement('li');
    listItem.className = 'list-group-item d-flex justify-content-between align-items-center';

    // Create the anchor element for the topic title
    const topicLink = document.createElement('a');
    topicLink.href = `/topic/${slug}/`;  // Use the slug to create the URL
    topicLink.textContent = title;  // Set the text to the topic title

    // Create a div for the additional information
    const infoDiv = document.createElement('div');
    infoDiv.className = 'd-flex flex-column align-items-end';

    // Create the paragraph for the author and date
    const authorDatePara = document.createElement('p');
    authorDatePara.className = 'text-muted mb-0';
    authorDatePara.textContent = `Posted by ${author} ${date}`;  // Set the author and date text

    // Create the span for the number of replies
    const repliesBadge = document.createElement('span');
    repliesBadge.className = 'badge bg-secondary';
    repliesBadge.textContent = `${replies} Replies`;  // Set the replies text

    // Append elements to their parents
    infoDiv.appendChild(authorDatePara);
    infoDiv.appendChild(repliesBadge);
    listItem.appendChild(topicLink);
    listItem.appendChild(infoDiv);

    return listItem;  // Return the complete list item
}

function handleScroll() {
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 100 && !isLoading) {
       loadTopics();
    }
}

// load objects dynmically when scrolling down
window.addEventListener('scroll', handleScroll);

// load dynamically first page of objects
document.addEventListener('DOMContentLoaded', loadTopics);
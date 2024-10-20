var page = 1;  // current page
var per_page = 5; // objects per page
var model = "Category";

function loadCategories() {
    let body = `page=${page}&per_page=${per_page}&model=${model}`;
    let filters = {};
    let categories = document.getElementById('categories');

    loadObjects(
        '/load-objects/',
        body,
        categories,
        filters,
        (object) => {
            return createCategory(object.name, `/category/${object.slug}/`, object.description);
        }
    );
}

function createCategory(name, url, description) {
    // Create the list item element
    const listItem = document.createElement("li");
    listItem.classList.add("list-group-item");

    // Create the heading element
    const heading = document.createElement("h5");

    // Create the anchor (link) element
    const link = document.createElement("a");
    link.href = url;  // Set the link URL
    link.textContent = name;  // Set the link text to the category name

    // Append the link to the heading
    heading.appendChild(link);

    // Create the paragraph for the description
    const paragraph = document.createElement("p");
    paragraph.textContent = description;  // Set the description text

    // Append the heading and paragraph to the list item
    listItem.appendChild(heading);
    listItem.appendChild(paragraph);

    return listItem;  // Return the constructed list item
}

function handleScroll() {
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 100 && !isLoading) {
       loadCategories();
    }
}

// load objects dynmically when scrolling down
window.addEventListener('scroll', handleScroll);

// load dynamically first page of objects
document.addEventListener('DOMContentLoaded', loadCategories);
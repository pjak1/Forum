var isLoading = false;

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function loadObjects(url , body, objectList, filters = {}, createObject) {
    if (isLoading) return;
    isLoading = true;

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: body
    })
    .then(response => response.json())
    .then(data => {
        data.objects.forEach(obj => {
            const newObject = createObject(obj);
            if (newObject) {
                addObject(objectList, () => newObject);
            }
        });

        if (data.has_next) {
            page++;
        } else {
            window.removeEventListener('scroll', handleScroll);
        }
        isLoading = false;
    })
    .catch(error => {
        console.error('Error:', error);
        isLoading = false;
    });
}

function addObject(objectList, createObject) {
    const object = createObject();
    objectList.appendChild(object);
}

const inputIds = [{
    textId: 'organization-search-form-input',
    resetId: 'organization-search-form-reset'
},
{
    textId: 'organization-datasets-search-form-input',
    resetId: 'organization-datasets-search-form-reset'
},
{
    textId: 'group-datasets-search-form-input',
    resetId: 'group-datasets-search-form-reset'
},
{
    textId: 'group-search-form-input',
    resetId: 'group-search-form-reset'
},
{
    textId: 'dataset-search-form-input',
    resetId: 'dataset-search-form-reset'
},
{
    textId: 'home-search-input-field',
    resetId: 'home-search-reset'
}];
inputIds.forEach(input => {
    const textId = document.getElementById(input.textId);
    const resetId = document.getElementById(input.resetId);
    if(textId && textId.value != ""){
        searchReset(resetId,textId);
    }
    if(textId){
        textId.addEventListener("keyup", function (e) {
            if (e.key === "Escape" || e.keyCode === KEYCODE.ESCAPE) {
                resetId.click();
            }
        });
    }
});

function searchReset(resetId, textId) {
    resetId.addEventListener("click", () => {
        textId.defaultValue = "";
        textId.focus();
    });
}
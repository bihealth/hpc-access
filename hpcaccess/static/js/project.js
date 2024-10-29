/* Project specific Javascript goes here. */


function mergeToJson() {
    var content = []
    $(".mergeToJson").each(function () {
        content.push('"' + $(this).attr("name") + '": "' + $(this).val() + '"');
    });
    $("#id_resources_requested").val("{" + content.join(", ") + "}")
}


function jsonToFields() {
    var jsonDict = $("#id_resources_requested").val();
    if (jsonDict !== null) {
        $.each(jQuery.parseJSON(jsonDict), function (key, value) {
            $("#id_" + key).val(value);
        })
    }
}


function buildSelectedMembers() {
    $("#membersSelected").empty();
    $("#id_members option:selected").each(function () {
        const id = $(this).val();
        const isOwner = id === $("#submit").data("owner-id").toString();
        let cancelButton = '';
        if (!isOwner) {
            cancelButton = `<a class="btn btn-secondary btn-sm float-end cancelMember" data-member-id="${id}" />
            <i class="iconify float-end cancelMember" data-icon="mdi:close"></i>
            </a>`;
        }

        let element = `<li class="list-group-item">
            ${$(this).text()}
            ${cancelButton}
        </li>`;
        $("#membersSelected").append(element);
    });
    $(".cancelMember").on('click', cancelMember)
}


function cancelMember() {
    var member_id = $(this).data("member-id");
    $(`#id_delegate option[value='${member_id}']`).remove();
    $(`#id_members option[value='${member_id}']`).remove();
    buildSelectedMembers();
}

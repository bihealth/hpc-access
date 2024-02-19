/* Project specific Javascript goes here. */


var delegate_id = null;


function buildSelectedMembers() {
    $("#membersSelected").empty();

    $("#id_members option:selected").each(function () {
        let id = $(this).val();
        let element = '<span class="badge bg-dark me-1">' + $(this).text();
        if (id !== delegate_id && id !== $("#submit").data("owner-id").toString()) {
            element += ' <span class="badge bg-danger rounded-pill text-bg-danger cancelMember" data-member-id="' + id + '">X</span>';
        }
        element += '</span>';
        $("#membersSelected").append(element);
    });

    $(".cancelMember").on('click', cancelMember)
}


function mergeToJson() {
    var content = [];
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


function consent() {
    if ($("#id_consent").is(':checked')) {
        $("#id_submit_button").removeClass("disabled");
    }
    else {
        $("#id_submit_button").addClass("disabled");
    }
}


function toggleInactiveMembers() {
    var members_inactive = $(".member_inactive");

    for (var i = 0; i < members_inactive.length(); i++) {
    }
}


function countInactiveMembers() {
    var members_inactive = $(".groupMemberInactive");
    $("#inactiveMembers").text(members_inactive.length);
}


function addOwnerMember() {
    var members = $("#id_members").val();
    members.push($("#submit").data("owner-id").toString());
    $("#id_members").val(members);
}


function addDelegateMember() {
    var members = $("#id_members").val();
    delegate_id = $("#id_delegate").val();
    var position = members.indexOf(delegate_id);

    if (position === -1) {
        console.error("Delegate (" + delegate_id + ") not found in list. List of members: " + members)
        return
    }

    if (delegate_id) {
        members.splice(position, 1);
        $("#id_members").val(members);
    }

    if (delegate_id) {
        members.push(delegate_id);
        $("#id_members").val(members);
    }

    console.log(members)

    buildSelectedMembers();
}


function addMember() {
    var member_id = $("#id_members_dropdown").val();

    if (member_id) {
        var members = $("#id_members").val();

        members.push(member_id);
        $("#id_members").val(members);

        buildSelectedMembers();
    }
}


function cancelMember() {
    var member_id = $(this).data("member-id");
    var members = $("#id_members").val();
    var position = members.indexOf(member_id.toString());

    if (position === -1) {
        console.error("Member (" + member_id + ") not found in list. List of members: " + members)
        return
    }

    members.splice(position, 1);

    $("#id_members").val(members);

    buildSelectedMembers();
}

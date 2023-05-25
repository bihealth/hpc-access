.. _pis:

PIs & Delegates
===============

.. important::

    Only principal investigators can request the creation of their group on the cluster.

Principal investigators can request the creation of their group on the cluster, add and remove users or request a new project.
A delegate for the group can be named by the PI that can take over the administrative work of managing the group in the PIs name.

.. toctree::
   :maxdepth: 2

Group requests
--------------

The main concern of a PI when interested in the BIH HPC cluster is how to get the group on the cluster.
This section describes this in more detail.

Request a group
^^^^^^^^^^^^^^^

This is possible if the PI has no account on the cluster and hasn't requested a group yet.
Once logged in as described in section :ref:`login`, the visitor will be greeted with a group request form.

The form has three fields and one of the is automatically filled out unchangably.
The expiry date of the group is automatically set to end of January of the next calendar year.
Please fill out a concise description of what the group is working on and provide an evidence that you are known to Charite or MDC as PI, for example a link to the lab page.
Professors are considered PI.

Retract a group request
^^^^^^^^^^^^^^^^^^^^^^^

A group request can be retracted as long as it hasn't been confirmed by the administrators.
Log in to the application and hit the retract button.
You will be able to re-submit the application.

Account overview
----------------

The upper panel line of three tiles contains information about the user, the group and projects.
It is the same for all users on the cluster and described in more detail in the :ref:`users` section.

Management panel
----------------

The management panel can be found under the user overview.
It comprises 3x3 tiles, while the first column is for requests regarding the group, the second column is for requests regarding the users and the last column is for requests regarding the projects.
The first row is for creating an object, the second row is for changing an object and the last row to remove an object.
The very first tile is empty as the group has already been created.

Make a request
--------------

Add a user to the group
^^^^^^^^^^^^^^^^^^^^^^^

When you have the confirmation that the group was created, you can add users to the group.
Find the add users tile (top row, middle column) and add a user by providing the institutional email address.

.. important::

   Only users with an IT account and valid email address with Charite or MDC can be added.

Users won't automatically appear in your group.
First, the HPC administrators have to confirm the request.
This triggers an invitation that is send out to the user and that he/she has to accept (or decline).

Request a user change
^^^^^^^^^^^^^^^^^^^^^

The only change in a user is to extend its expiry date.
Find the change users tile (middle row, middle column) and select the user you want to change.
The request has to be confirmed by the HPC administrators to take effect.

Remove a user from the group
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is not implemented yet.

Request a change in group
^^^^^^^^^^^^^^^^^^^^^^^^^

You can request a different storage quota on the cluster, add, change or remove the delegate and change the expiry date of the group.
Find the change group tile (middle row, first column) and make the request.
It has first to be confirmed by the HPC administrators to take effect.

Request a project
^^^^^^^^^^^^^^^^^

You can request a new project and add users from different groups to that project.
If a delegate requests the project, the group owner will be registered as project owner.
As with the group, a delegate can be named for the project that can add users and make changes.
Find the add project tile (first row, last column) and provide a concise name for the project.

Add a user to a project
^^^^^^^^^^^^^^^^^^^^^^^

To add a user to a project, find the change project tile (middle row, last column).

Remove a user from a project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is not implemented yet.

Manage a request
----------------

Request details
^^^^^^^^^^^^^^^

After posting a request, it will be listed in the associated tile and have a link to the details as well as a small status information.
A request can have different statuses:

1. **pending:** The request is active. The admins are in charge of deciding the request.
2. **revision required:** The admins decided that the request needs to be revised by the requester.
3. **pending (revised):** The request is active after being revised by the requester.
4. **approved:** The request has been approved by the admins.
5. **denied:** The request has been denied by the admins.
6. **retracted:** The request has been retracted by the requester before admins decided the request.

Invitations have a slightly different set of statuses:

1. **pending:** The invitation is active and the user needs to accept or decline it.
2. **accepted:** The invited user has accepted the invitation.
3. **rejected:** The invited user has rejected the invitation.
4. **expired:** The invitiation has expired. Expiration time needs to be defined (TODO)

Retract any request
^^^^^^^^^^^^^^^^^^^

Any request posted can be retracted.
Just go to the request details and find the retract button in the top right corner.

Communication with the admins
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If the administrators need more information, they will drop a note that will show up in the ticket.
This also changes the status of the ticket, and you need to resolve this by changing the request as requested and/or drop a note to the administrators.

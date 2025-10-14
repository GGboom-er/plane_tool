Isaac Newton Physics

Isaac Newton Physics is a Maya tool designed to create realistic prop animations automatically, without the need to keyframe everything by hand.
It leverages Maya’s legacy rigid body system to simulate physics quickly, then bakes the motion onto your controllers or meshes for final use in production.

Features

Quick Setup
Assign Sim Mesh, Colliders, and Destination easily. Works with multiple meshes and colliders.

Automatic Handoff
Simulation start and stop are controlled by the timeline. Build jumps to the correct start frame automatically.

Physics Controls
Adjust values such as friction, bounciness, damping, gravity, and direction until the motion feels right.

Bake Animation
Once satisfied, bake directly onto your chosen destination controller or mesh.

Reset Physics
Reset to restore all physics settings to their defaults.

Collision Support
Works even if your colliders have animation applied.

Installing
Just Drag NEWTON_Drag_install.py to viewport and Select IsaacNewton Folder


Warning

Please be aware that Maya may lag or even freeze if:

You assign too many collider meshes at once.

Your collider meshes or simulation meshes have a very high polycount.

For best performance:

Use low-resolution proxy meshes as colliders whenever possible.

Keep the number of colliders to a minimum.

Hide or delete unnecessary geometry before running the simulation.
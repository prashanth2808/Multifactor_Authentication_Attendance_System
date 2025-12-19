# cli/register.py
"""
Register a new user with 3 face photos + 3 voice clips
Command: python main.py register --name "Name" --email "email@x.com"
REFACTORED: Now uses unified registration service for consistency
"""

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from utils.camera import capture_face_burst
from services.registration_service import registration_service

console = Console()

def register(
    name: str = typer.Option(..., "--name", "-n", help="Full name of the user"),
    email: str = typer.Option(..., "--email", "-e", help="Email address"),
    user_type: str = typer.Option(None, "--user-type", help="User type: student or faculty"),
    student_class: str = typer.Option(None, "--class", help="Student class if user-type=student"),
    phone: str = typer.Option(None, "--phone", help="Phone number (10+ digits)")
):
    """
    Capture 3 face photos + 3 voice clips, generate embeddings, save to MongoDB
    Now uses UNIFIED registration service for consistency with Flask
    Enhanced with user type and class/phone collection
    """
    console.print("\n[bold blue]🚀 CLI REGISTRATION STARTING[/bold blue]")
    console.print("[cyan]Using unified registration service...[/cyan]")
    
    # === COLLECT USER TYPE AND ADDITIONAL INFO ===
    console.print("\n[yellow]📋 Collecting additional user information...[/yellow]")
    
    # Ask for or validate user type
    import click
    if user_type is None:
        user_type = typer.prompt(
            "Are you a student or faculty member?",
            type=click.Choice(["student", "faculty"], case_sensitive=False),
            default="student"
        )
    else:
        user_type = user_type.strip().lower()
        if user_type not in ("student", "faculty"):
            console.print("[red]--user-type must be 'student' or 'faculty'[/red]")
            raise typer.Exit(code=2)

    # Student class (only for students)
    if user_type == "student":
        if not student_class:
            console.print("\n[cyan]Select your class:[/cyan]")
            classes = ["M.Sc in AI", "M.Sc in CS", "M.Sc in BA", "M.Tech in AI", "M.Tech in CS"]
            for i, cls in enumerate(classes, 1):
                console.print(f"  {i}. {cls}")
            while True:
                try:
                    choice = typer.prompt("Enter choice (1-5)", type=int)
                    if 1 <= choice <= 5:
                        student_class = classes[choice - 1]
                        console.print(f"[green]Selected: {student_class}[/green]")
                        break
                    else:
                        console.print("[red]Please enter a number between 1-5[/red]")
                except ValueError:
                    console.print("[red]Please enter a valid number[/red]")
        else:
            student_class = student_class.strip()
    else:
        student_class = None

    # Phone number (required for all)
    if not phone:
        phone = typer.prompt("Enter your phone number")
    phone = phone.strip()
    while len(phone) < 10 or not phone.isdigit():
        console.print("[red]Phone number must be at least 10 digits and numeric[/red]")
        phone = typer.prompt("Enter your phone number").strip()
    console.print(f"[green]Phone number: {phone}[/green]")

    console.print(f"\n[green]✅ User Information Collected:[/green]")
    console.print(f"   👤 Name: {name}")
    console.print(f"   📧 Email: {email}")
    console.print(f"   🏢 Type: {user_type.title()}")
    if user_type == "student":
        console.print(f"   🎓 Class: {student_class}")
    console.print(f"   📞 Phone: {phone}")
    
    # === FACE CAPTURE (BURST MODE) ===
    console.print("\n[yellow]Capturing 3 face photos in burst mode...[/yellow]")
    console.print("[cyan]Look at camera → Press SPACE once for 3 photos[/cyan]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        task = progress.add_task("Preparing camera...", total=None)

        face_images = capture_face_burst()
        
        if face_images is None or len(face_images) != 3:
            console.print("[bold red]Failed to capture 3 valid face photos[/bold red]")
            console.print("[yellow]Try in better lighting or check camera[/yellow]")
            raise typer.Exit(code=1)

        progress.update(task, description="Face capture complete!", total=3, completed=3)

    console.print("[bold green]✅ All 3 face photos captured![/bold green]")

    # === CALL UNIFIED REGISTRATION SERVICE ===
    console.print("\n[yellow]🔄 Processing registration through unified service...[/yellow]")
    
    # Prepare additional user data
    additional_data = {
        "user_type": user_type,
        "student_class": student_class,
        "phone": phone
    }
    
    # Call the unified registration service
    result = registration_service.register_user(
        name=name,
        email=email,
        face_data=face_images,  # Pass OpenCV images
        voice_data=None,        # CLI records voice live
        source="cli",
        additional_data=additional_data
    )
    
    # Handle results
    if result["success"]:
        console.print(f"\n[bold green]🎉 CLI REGISTRATION SUCCESSFUL![/bold green]")
        console.print(f"✅ User ID: [bold cyan]{result['user_id']}[/bold cyan]")
        console.print(f"📁 Photos: {result['face_embeddings_count']} saved")
        console.print(f"🎤 Voice: {result['voice_embedding_dimension']}D embedding")
        console.print(f"📂 Folder: [yellow]{result['photo_folder']}[/yellow]")
    else:
        console.print(f"[bold red]❌ REGISTRATION FAILED[/bold red]")
        console.print(f"[red]Error at {result.get('stage', 'unknown')} stage:[/red]")
        console.print(f"[red]{result['error']}[/red]")
        raise typer.Exit(code=1)
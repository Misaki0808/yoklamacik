using System.ComponentModel.DataAnnotations;

namespace Entities
{
    /// <summary>
    /// This represent the teacher Entity
    /// </summary>
    public class Teacher
    {
        public Guid Id { get;}
        public string? UserName { get; set; }
        public string? Email { get; set; }
        public string? Password { get; set; }
        public Dictionary<string, string>? Lessons { get; set; }
    }
}

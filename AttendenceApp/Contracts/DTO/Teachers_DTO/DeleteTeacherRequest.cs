using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace ServiceContracts.DTO.Teachers_DTO
{
    /// <summary>
    /// This Represents the Deleting Request Entity for Teacher Entity
    /// </summary>
    public record DeleteTeacherRequest
    {
        [Required]
        public Guid Id { get; }

        [Required]
        [MaxLength(50)]
        public string? UserName { get; set; }
        [Required]
        [EmailAddress]
        [MaxLength(80)]
        public string? Email { get; set; }
        [Required]
        [RegularExpression(@"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{8,15}$")]
        public string? Password { get; set; }
        public Dictionary<string, string>? Lessons { get; set; }
    }
}

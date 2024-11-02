using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace ServiceContracts.DTO.Teachers_DTO
{
    /// <summary>
    /// This Represents the Teacher Response Object Entity for Teacher Entity
    /// </summary>
    public record TeacherResponse
    {
        public Guid Id { get; }
        public string? UserName { get; set; }
        public string? Email { get; set; }
        public string? Password { get; set; }
        public Dictionary<string, string>? Lessons { get; set; }
    }
}
